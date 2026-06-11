"""API pública por org (Bearer `Organization.api_key`).

Permite que sistemas externos da própria org criem/atualizem um contato e,
opcionalmente, disparem uma automação — sem passar pelo app nem pelo WhatsApp.
Reusa a infra existente: `normalize_phone`, `check_contact_limit`, Pipedrive sync,
`trigger_event('contact.created')` e o motor de automação (`run_automation`).
"""
from ninja import Router, Schema
from typing import Optional

from .models import Contact
from .schemas import ContactOut
from core.api_key_auth import ApiKeyAuth
from core.utils.errors import GenericErrorSchema
from core.utils.phone import normalize_phone
from integrations.models import PipedriveIntegration
from integrations.pipedrive_tasks import sync_contact_to_pipedrive

router = Router(tags=['Public API'], auth=ApiKeyAuth())


class PublicContactIn(Schema):
    name: str
    phone: str
    email: Optional[str] = None
    custom_fields: dict = {}
    # Dispara uma automação específica pelo id (override preciso, opcional).
    automation_id: Optional[int] = None
    # Roteamento do gatilho 'api.request': automações com trigger_filters
    # {'source': <x>} só rodam se este valor casar. None = roda as sem filtro.
    source: Optional[str] = None


class PublicContactOut(Schema):
    contact: ContactOut
    created: bool
    automation_started: bool


@router.post('/contacts', response={200: PublicContactOut, 201: PublicContactOut, 400: GenericErrorSchema})
def create_public_contact(request, data: PublicContactIn):
    from billing.services import check_contact_limit
    from automations.models import Automation, AutomationRun

    org = request.auth  # ApiKeyAuth devolve a Organization

    phone = normalize_phone(data.phone)
    if not phone:
        return 400, GenericErrorSchema(detail='Telefone inválido')

    # Valida automação (se pedida) ANTES de mexer no contato.
    automation = None
    if data.automation_id is not None:
        automation = Automation.objects.filter(
            id=data.automation_id, organization=org, is_active=True,
        ).first()
        if automation is None:
            return 400, GenericErrorSchema(detail='Automação inválida ou inativa')

    contact = Contact.objects.filter(organization=org, phone=phone).first()
    created = contact is None

    if created:
        if not check_contact_limit(org):
            return 400, GenericErrorSchema(detail='Limite de contatos atingido no plano atual')
        contact = Contact.objects.create(
            organization=org, name=data.name, phone=phone,
            email=data.email, custom_fields=data.custom_fields or {},
        )
    else:
        contact.name = data.name or contact.name
        if data.email:
            contact.email = data.email
        if data.custom_fields:
            merged = dict(contact.custom_fields or {})
            merged.update(data.custom_fields)
            contact.custom_fields = merged
        contact.save()

    if PipedriveIntegration.objects.filter(organization=org, is_active=True).exists():
        sync_contact_to_pipedrive.delay(contact.id)

    from automations.events import trigger_event

    # contact.created só na criação nova → idempotente p/ retries da integração.
    if created:
        trigger_event('contact.created', org.id, contact_id=contact.id)

    # api.request dispara em TODA chamada (cada requisição é um evento HTTP) —
    # caminho idiomático sem precisar de automation_id. Roteável por `source`.
    trigger_event('api.request', org.id, contact_id=contact.id, source=data.source)

    automation_started = False
    if automation is not None:
        from automations.tasks import run_automation
        run = AutomationRun.objects.create(
            automation=automation, context={'contact_id': contact.id},
        )
        run_automation.delay(run.id)
        automation_started = True

    status = 201 if created else 200
    return status, {'contact': contact, 'created': created, 'automation_started': automation_started}
