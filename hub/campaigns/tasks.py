from django.utils import timezone
from django.db.models import F
import random
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def run_campaign(campaign_id: int):
    from campaigns.models import Campaign, CampaignContact

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return

    contacts = list(CampaignContact.objects.filter(campaign=campaign, status='pending'))
    if not contacts:
        Campaign.objects.filter(id=campaign_id).update(status=Campaign.Status.FINISHED, finished_at=timezone.now())
        return

    Campaign.objects.filter(id=campaign_id).update(
        status=Campaign.Status.RUNNING,
        started_at=timezone.now()
    )

    for i, cc in enumerate(contacts):
        delay = i * random.uniform(campaign.interval_min, campaign.interval_max)
        send_campaign_message.apply_async(args=[cc.id], countdown=delay)

@shared_task
def send_campaign_message(campaign_contact_id: int):
    from campaigns.models import Campaign, CampaignContact
    from conversations.models import Conversation, Message
    from integrations.services import send_message

    try:
        cc = CampaignContact.objects.select_related('campaign__instance', 'campaign__agent', 'contact').get(id=campaign_contact_id)
    except CampaignContact.DoesNotExist:
        return

    campaign = cc.campaign

    if campaign.status in (Campaign.Status.PAUSED, Campaign.Status.CANCELLED):
        return

    if cc.status != CampaignContact.Status.PENDING:
        return
    
    messages = list(campaign.messages.all())
    if not messages:
        CampaignContact.objects.filter(id=cc.id).update(status=CampaignContact.Status.SKIPPED, error='Nenhuma variante de mensagem')
        check_campaign_completion.delay(campaign.id)
        return
    
    chosen = random.choice(messages)
    contact = cc.contact
    instance = campaign.instance

    content = chosen.content
    content = content.replace('{nome}', contact.name or '')
    content = content.replace('{telefone}', contact.phone or '')

    try:
        conversation = Conversation.objects.filter(
            organization=campaign.organization,
            contact=contact,
            instance=instance,
            status=Conversation.Status.OPEN
        ).first()

        if not conversation:
            conversation = Conversation.objects.create(
                organization=campaign.organization,
                contact=contact,
                instance=instance,
                agent=campaign.agent,
                ai_active=bool(campaign.agent) and campaign.ai_active,
                campaign=campaign
            )
        else:
            update_fields = ['campaign']
            if campaign.agent and not conversation.agent:
                conversation.agent = campaign.agent
                conversation.ai_active = campaign.ai_active
                update_fields += ['agent', 'ai_active']
            conversation.campaign = campaign
            conversation.save(update_fields=update_fields)

        send_message(
            instance_api_key=instance.instance_api_key,
            phone=contact.phone,
            text=content
        )

        Message.objects.create(
            conversation=conversation,
            role=Message.Role.OPERATOR,
            content=content
        )

        CampaignContact.objects.filter(id=cc.id).update(
            status=CampaignContact.Status.SENT,
            message_sent=content,
            conversation=conversation,
            sent_at=timezone.now()
        )

        Campaign.objects.filter(id=campaign.id).update(sent_count=F('sent_count') + 1)
            
    except Exception as exc:
        logger.error(f'[send_campaign_message] Falha contato {contact.id}: {exc}')
        CampaignContact.objects.filter(id=cc.id).update(
            status=CampaignContact.Status.FAILED,
            error=str(exc)
        )
        Campaign.objects.filter(id=campaign.id).update(failed_count=F('failed_count') + 1)

    finally:
        check_campaign_completion.delay(campaign.id)

@shared_task
def check_campaign_completion(campaign_id: int):
    from campaigns.models import Campaign, CampaignContact

    pending = CampaignContact.objects.filter(
        campaign_id=campaign_id,
        status=CampaignContact.Status.PENDING
    ).exists()

    if not pending:
        Campaign.objects.filter(id=campaign_id, status=Campaign.Status.RUNNING).update(status=Campaign.Status.FINISHED, finished_at=timezone.now())

