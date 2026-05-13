from celery import shared_task
from integrations.models import PipedriveIntegration
from integrations.pipedrive_services import create_or_update_person, create_deal, close_deal, create_note
import logging
import httpx

logger = logging.getLogger(__name__)


def _is_auth_error(exc) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (401, 403)
    return False


def _disable_integration_on_auth(integration, exc):
    if _is_auth_error(exc):
        logger.warning('Pipedrive auth failed (org=%s) — desativando integração', integration.organization_id)
        PipedriveIntegration.objects.filter(id=integration.id).update(is_active=False)
        return True
    return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_contact_to_pipedrive(self, contact_id: int):
    from contacts.models import Contact
    try:
        contact = Contact.objects.select_related('organization').get(id=contact_id)
    except Contact.DoesNotExist:
        logger.info('sync_contact_to_pipedrive: contact %s não existe, skip', contact_id)
        return

    try:
        integration = PipedriveIntegration.objects.get(organization=contact.organization)
    except PipedriveIntegration.DoesNotExist:
        return
    if not integration.is_active or not integration.sync_contacts:
        return

    try:
        person_id = create_or_update_person(integration.api_key, contact)
        if person_id:
            Contact.objects.filter(id=contact_id).update(pipedrive_person_id=person_id)
    except Exception as exc:
        logger.error(f'sync_contact_to_pipedrive error: {exc}')
        if _disable_integration_on_auth(integration, exc):
            return
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_deal_from_conversation(self, conversation_id: int):
    from conversations.models import Conversation
    from contacts.models import Contact as ContactModel

    try:
        conv = Conversation.objects.select_related('contact', 'organization').get(id=conversation_id)
    except Conversation.DoesNotExist:
        return

    try:
        integration = PipedriveIntegration.objects.get(
            organization=conv.organization, is_active=True, auto_create_deal=True
        )
    except PipedriveIntegration.DoesNotExist:
        return

    if not integration.deal_pipeline_id or not integration.deal_stage_id:
        return

    try:
        fresh_contact = ContactModel.objects.get(id=conv.contact_id)
    except ContactModel.DoesNotExist:
        return

    try:
        person_id = fresh_contact.pipedrive_person_id
        if not person_id:
            if integration.sync_contacts:
                raise self.retry(countdown=5, max_retries=5)
            person_id = create_or_update_person(integration.api_key, fresh_contact)
            if person_id:
                ContactModel.objects.filter(id=conv.contact_id).update(pipedrive_person_id=person_id)

        if not person_id:
            return

        deal_id = create_deal(
            api_key=integration.api_key,
            title=f'WhatsApp: {conv.contact.name}',
            person_id=person_id,
            pipeline_id=integration.deal_pipeline_id,
            stage_id=integration.deal_stage_id,
        )
        if deal_id:
            conv.__class__.objects.filter(id=conversation_id).update(pipedrive_deal_id=deal_id)

    except Exception as exc:
        logger.error(f'create_deal_from_conversation error: {exc}')
        if _disable_integration_on_auth(integration, exc):
            return
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def close_deal_from_conversation(self, conversation_id: int, won: bool = True):
    from conversations.models import Conversation
    try:
        conv = Conversation.objects.select_related('organization').get(id=conversation_id)
    except Conversation.DoesNotExist:
        return

    if not conv.pipedrive_deal_id:
        return

    try:
        integration = PipedriveIntegration.objects.get(
            organization=conv.organization, is_active=True, auto_close_deal=True
        )
    except PipedriveIntegration.DoesNotExist:
        return

    try:
        close_deal(integration.api_key, conv.pipedrive_deal_id, won=won)
    except Exception as exc:
        logger.error(f'close_deal_from_conversation error: {exc}')
        if _disable_integration_on_auth(integration, exc):
            return
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_annotation_to_pipedrive(self, annotation_id: int):
    from contacts.models import ContactAnnotation
    from conversations.models import Conversation

    try:
        ann = ContactAnnotation.objects.select_related('contact', 'organization').get(id=annotation_id)
    except ContactAnnotation.DoesNotExist:
        return

    try:
        integration = PipedriveIntegration.objects.get(organization=ann.organization, is_active=True)
    except PipedriveIntegration.DoesNotExist:
        return

    conv = Conversation.objects.filter(
        contact=ann.contact,
        organization=ann.organization,
        pipedrive_deal_id__isnull=False
    ).order_by('-started_at').first()

    if not conv:
        return

    try:
        create_note(integration.api_key, conv.pipedrive_deal_id, ann.content, pinned=ann.pinned)
    except Exception as exc:
        logger.error(f'sync_annotation_to_pipedrive error: {exc}')
        if _disable_integration_on_auth(integration, exc):
            return
        raise self.retry(exc=exc)
