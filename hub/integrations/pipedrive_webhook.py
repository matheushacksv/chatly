import logging
from ninja import Router
from django.shortcuts import get_object_or_404
from integrations.models import PipedriveIntegration
from contacts.models import Contact
from core.utils.phone import normalize_phone

logger = logging.getLogger(__name__)

router = Router(tags=['Pipedrive Webhook'])


def _extract_phone(person: dict) -> str | None:
    phones = person.get('phones') or person.get('phone') or []
    if isinstance(phones, list):
        for p in phones:
            value = p.get('value') if isinstance(p, dict) else str(p)
            if value:
                return normalize_phone(value)
    return None


def _extract_email(person: dict) -> str | None:
    emails = person.get('emails') or person.get('email') or []
    if isinstance(emails, list):
        for e in emails:
            value = e.get('value') if isinstance(e, dict) else str(e)
            if value:
                return value
    return None


@router.post('/{webhook_secret}', auth=None)
def pipedrive_webhook(request, webhook_secret: str):
    integration = get_object_or_404(
        PipedriveIntegration,
        webhook_secret=webhook_secret,
        is_active=True,
    )
    org = integration.organization

    try:
        body = request.body_json if hasattr(request, 'body_json') else __import__('json').loads(request.body)
    except Exception:
        return {'ok': False}

    event = body.get('event', '')        # e.g. "added.person"
    obj_type = body.get('meta', {}).get('object', '')
    current = body.get('current') or {}  # novo estado
    previous = body.get('previous') or {}  # estado anterior (updates)

    if obj_type != 'person':
        return {'ok': True}

    action = event.split('.')[0]  # added | updated | deleted | merged

    person_id = (current or previous).get('id')
    if not person_id:
        return {'ok': True}

    if action == 'deleted' or action == 'merged':
        for contact in Contact.objects.filter(organization=org, pipedrive_person_id=person_id):
            contact.custom_fields = {**contact.custom_fields, 'pipedrive_archived': True}
            contact.save(update_fields=['custom_fields', 'updated_at'])
        logger.info(f'Pipedrive webhook: person {person_id} deleted/merged — contact archived')
        return {'ok': True}

    # added ou updated
    name = current.get('name') or ''
    phone = _extract_phone(current)
    email = _extract_email(current)

    if not phone and not email:
        return {'ok': True}

    # tenta encontrar pelo pipedrive_person_id primeiro
    contact = Contact.objects.filter(organization=org, pipedrive_person_id=person_id).first()

    if not contact and phone:
        contact = Contact.objects.filter(organization=org, phone=phone).first()

    if not contact and email:
        contact = Contact.objects.filter(organization=org, email=email).first()

    if contact:
        # atualiza
        if name:
            contact.name = name
        if email:
            contact.email = email
        if phone:
            contact.phone = phone
        contact.pipedrive_person_id = person_id
        contact.save(update_fields=['name', 'email', 'phone', 'pipedrive_person_id', 'updated_at'])
        logger.info(f'Pipedrive webhook: contact {contact.id} updated from person {person_id}')
    else:
        # cria novo
        Contact.objects.create(
            organization=org,
            name=name or phone or email,
            phone=phone,
            email=email,
            pipedrive_person_id=person_id,
        )
        logger.info(f'Pipedrive webhook: new contact created from person {person_id}')

    return {'ok': True}


