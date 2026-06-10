import re
import logging

logger = logging.getLogger(__name__)


def _jid_user(jid: str) -> str:
    """Parte de usuário de um JID, sem sufixo de dispositivo (``:NN``) nem agente (``.N``).

    Ex.: ``557499879409:38@s.whatsapp.net`` → ``557499879409``.
    Necessário porque ``normalize_phone`` remove não-dígitos e concatenaria o ``:38``.
    """
    local = jid.split('@', 1)[0]
    local = local.split(':', 1)[0]
    local = local.split('.', 1)[0]
    return local


def resolve_sender_phone(info: dict) -> tuple[str, bool]:
    """Resolve o telefone real do remetente a partir do bloco ``Info`` do webhook.

    WhatsApp moderno usa LID (Linked ID, ``<id>@lid``) como identificador, que NÃO
    é um telefone. Os papéis de ``Sender``/``SenderAlt`` se invertem conforme o
    endereçamento: em PN, ``Sender`` é o telefone (``@s.whatsapp.net``, possivelmente
    com sufixo ``:device``) e ``SenderAlt`` é o LID; em LID, ``Sender`` é o LID e
    ``SenderAlt`` traz o telefone real. Por isso preferimos sempre o JID de telefone.

    Retorna ``(telefone_normalizado, is_lid)``. ``is_lid=True`` indica que só havia
    LID disponível — o valor retornado é o próprio LID (fallback), não um telefone.
    """
    candidates = [
        info.get('Sender', '') or '',
        info.get('SenderAlt', '') or '',
        info.get('Chat', '') or '',
        info.get('ChatAlt', '') or '',
    ]
    pn = next((c for c in candidates if '@s.whatsapp.net' in c), '')
    if pn:
        return normalize_phone(_jid_user(pn)), False

    raw = info.get('Sender', '') or ''
    is_lid = raw.endswith('@lid') or (info.get('AddressingMode') == 'lid')
    if is_lid:
        # Telefone real não veio no payload — registra para mapear o campo correto.
        logger.warning('[resolve_sender_phone] só LID disponível; Info=%s', info)
    return normalize_phone(_jid_user(raw)), is_lid


def normalize_phone(phone: str) -> str:
    """
    Normaliza número de telefone para o formato internacional sem símbolos.

    Regra brasileira: números com código 55 + DDD (2 dígitos) + 8 dígitos
    (total 12) recebem o 9 inserido após o DDD, ficando com 13 dígitos.

    Exemplos:
        554896436646  → 5548996436646  (adiciona 9 após DDD)
        5548996436646 → 5548996436646  (já normalizado)
        5511999999999 → 5511999999999  (já normalizado)
    """
    phone = re.sub(r'\D', '', phone)

    if phone.startswith('55') and len(phone) == 12:
        phone = phone[:4] + '9' + phone[4:]

    return phone
