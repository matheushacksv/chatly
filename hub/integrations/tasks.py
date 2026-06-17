import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Após N tentativas de /connect sem logar, assume logout real -> needs_qr (badge).
MAX_RECONNECT_ATTEMPTS = 5


def _webhook_url(instance) -> str:
    return f'{settings.BASE_URL}/api/webhooks/whatsapp/{instance.instance_name}/'


@shared_task
def reconnect_instance(instance_id: int):
    """Reconcilia o estado real da instância (via /instance/status) e, se for o caso
    recuperável (socket caído com cred), dispara /connect. Distingue:
      - LoggedIn=true            -> CONNECTED, zera contadores.
      - Connected & !LoggedIn    -> needs_qr (fantasma/logout): NÃO conecta, pede QR.
      - Connected=false          -> /connect (recuperável). Excede threshold -> needs_qr.
    Idempotente; seguro p/ rodar em paralelo (1 por instância)."""
    from integrations.models import WhatsAppInstance
    from integrations import services

    inst = WhatsAppInstance.objects.filter(id=instance_id).first()
    if inst is None or inst.needs_qr:
        return  # logout real -> espera humano escanear; não martela o EvoGO

    try:
        data = services.get_status(inst.instance_api_key).get('data', {})
    except Exception as e:
        logger.warning('[reconnect_instance %s] get_status falhou: %s', instance_id, e)
        data = {}

    status, needs_qr = services.classify_status(data)

    if status == WhatsAppInstance.Status.CONNECTED:
        WhatsAppInstance.objects.filter(id=instance_id).update(
            status=WhatsAppInstance.Status.CONNECTED, needs_qr=False,
            reconnect_attempts=0, last_seen_at=timezone.now(),
        )
        return

    if needs_qr:
        WhatsAppInstance.objects.filter(id=instance_id).update(
            status=WhatsAppInstance.Status.DISCONNECTED, needs_qr=True,
        )
        logger.warning('[reconnect_instance %s] LoggedIn=false -> needs QR', instance_id)
        return

    # Connected=false -> tenta reconectar (auto-loga se a cred ainda existe no gateway)
    attempts = inst.reconnect_attempts + 1
    try:
        services.connect_instance(inst.instance_api_key, _webhook_url(inst))
        WhatsAppInstance.objects.filter(id=instance_id).update(
            status=WhatsAppInstance.Status.CONNECTING, reconnect_attempts=attempts,
        )
    except Exception as e:
        logger.warning('[reconnect_instance %s] connect falhou: %s', instance_id, e)
        WhatsAppInstance.objects.filter(id=instance_id).update(reconnect_attempts=attempts)

    if attempts >= MAX_RECONNECT_ATTEMPTS:
        WhatsAppInstance.objects.filter(id=instance_id).update(
            needs_qr=True, status=WhatsAppInstance.Status.DISCONNECTED,
        )
        logger.warning('[reconnect_instance %s] %s tentativas -> needs QR', instance_id, attempts)


@shared_task
def sweep_instances():
    """Rede de segurança (Celery Beat): re-tenta SÓ o conjunto caído (não todas as
    instâncias), com fan-out 1 task/instância -> paralelo no pool, escala."""
    from integrations.models import WhatsAppInstance

    ids = list(
        WhatsAppInstance.objects.exclude(needs_qr=True)
        .filter(status__in=[
            WhatsAppInstance.Status.DISCONNECTED,
            WhatsAppInstance.Status.CONNECTING,
        ])
        .values_list('id', flat=True)
    )
    for iid in ids:
        reconnect_instance.delay(iid)
    return len(ids)
