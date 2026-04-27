from ninja import Router
from .models import CampaignContact, Campaign, CampaignMessage
from .schemas import CampaignIn, CampaignOut, CampaignContactOut, CampaignMessageIn, CampaignPatchIn, AddContactsIn
from .tasks import run_campaign, send_campaign_message
import random
from integrations.models import WhatsAppInstance
from agents.models import AIAgent
from contacts.models import Contact
from core.utils.errors import GenericErrorSchema, ErrorWithCodeSchema
from django.db.models import Q
from django.shortcuts import get_object_or_404
import logging

logger = logging.getLogger(__name__)
router = Router(tags=['Campaigns'])

#* ----- Campaigns [Rotas Estáticas] -----

@router.get('/', response=list[CampaignOut])
def list_campaigns(request):
    return Campaign.objects.filter(organization=request.auth.organization).prefetch_related('messages').order_by('-created_at')

@router.post('/', response={201: CampaignOut, 400: ErrorWithCodeSchema})
def create_campaign(request, data: CampaignIn):
    
    if not data.messages:
        return 400, ErrorWithCodeSchema(detail='Adicione ao menos uma variante de mensagem', code='no_messages')

    try:
        instance = WhatsAppInstance.objects.get(id=data.instance_id, organization=request.auth.organization)
    except WhatsAppInstance.DoesNotExist:
        return 400, ErrorWithCodeSchema(detail='Instância não encontrada', code='instance_not_found')

    agent = None
    if data.agent_id:
        try:
            agent = AIAgent.objects.get(id=data.agent_id, organization=request.auth.organization)
        except AIAgent.DoesNotExist:
            return 400, ErrorWithCodeSchema(detail='Agente não encontrado', code='agent_not_found')

    campaign = Campaign.objects.create(
        organization=request.auth.organization,
        name=data.name,
        instance=instance,
        agent=agent,
        ai_active=data.ai_active,
        interval_min=data.interval_min,
        interval_max=data.interval_max,
        created_by=request.auth,
    )

    for i, msg in enumerate(data.messages):
        CampaignMessage.objects.create(campaign=campaign, content=msg.content, order=i)

    return 201, campaign

#* ----- Campaigns [Rotas parametizdas] -----

@router.get('/{campaign_id}/', response={200: CampaignOut, 404: GenericErrorSchema})
def get_campaign(request, campaign_id: int):
    campaign = get_object_or_404(Campaign, id=campaign_id, organization=request.auth.organization)
    return campaign


@router.patch('/{campaign_id}/', response={200: CampaignOut, 400: ErrorWithCodeSchema, 404: GenericErrorSchema})
def update_campaign(request, campaign_id: int, data: CampaignPatchIn):

    campaign = get_object_or_404(Campaign, id=campaign_id, organization=request.auth.organization)

    if campaign.status != Campaign.Status.DRAFT:
        return 400, ErrorWithCodeSchema(detail='Só é possível editar campanhas em rascunho', code='not_draft')

    if data.name is not None:
        campaign.name = data.name
    if data.ai_active is not None:
        campaign.ai_active = data.ai_active
    if data.interval_min is not None:
        campaign.interval_min = data.interval_min
    if data.interval_max is not None:
        campaign.interval_max = data.interval_max

    if data.instance_id is not None:
        try:
            campaign.instance = WhatsAppInstance.objects.get(id=data.instance_id, organization=request.auth.organization)
        except WhatsAppInstance.DoesNotExist:
            return 400, ErrorWithCodeSchema(detail='Instância não encontrada', code='instance_not_found')

    if data.agent_id is not None:
        try:
            campaign.agent = AIAgent.objects.get(id=data.agent_id, organization=request.auth.organization)
        except AIAgent.DoesNotExist:
            return 400, ErrorWithCodeSchema(detail='Agente não encontrado', code='agent_not_found')

    campaign.save()

    if data.messages is not None:
        campaign.messages.all().delete()
        for i, msg in enumerate(data.messages):
            CampaignMessage.objects.create(campaign=campaign, content=msg.content, order=i)

    return campaign

@router.delete('/{campaign_id}/', response={204: None, 400: ErrorWithCodeSchema})
def delete_campaign(request, campaign_id: int):
    campaign = get_object_or_404(Campaign, id=campaign_id, organization=request.auth.organization)

    if campaign.status != Campaign.Status.DRAFT:
        return 400, ErrorWithCodeSchema(detail='Só é possivel excluir campanhas em rascunho', code='no_draft')

    campaign.delete()
    return 204, None

@router.post('/{campaign_id}/start/', response={200: CampaignOut, 400: ErrorWithCodeSchema})
def start_campaign(request, campaign_id: int):

    campaign = get_object_or_404(Campaign, id=campaign_id, organization=request.auth.organization)

    if campaign.status != Campaign.Status.DRAFT:
        return 400, ErrorWithCodeSchema(detail='Campanha não está em rascunho', code='invalid_status')

    if not campaign.messages.exists():
        return 400, ErrorWithCodeSchema(detail='Adicione ao menos uma variante de mensagem', code='no_messages')

    if not campaign.contacts.filter(status='pending').exists():
        return 400, ErrorWithCodeSchema(detail='Adicione ao menos um contato', code='no_contacts')

    run_campaign.delay(campaign.id)
    return campaign

@router.post('/{campaign_id}/pause/', response={200: CampaignOut, 400: ErrorWithCodeSchema})
def pause_campaign(request, campaign_id: int):
    campaign = get_object_or_404(Campaign, id=campaign_id, organization=request.auth.organization)

    if campaign.status != Campaign.Status.RUNNING:
        return 400, ErrorWithCodeSchema(detail='Campanha não está em execução', code='invalid_status')

    campaign.status = Campaign.Status.PAUSED
    campaign.save(update_fields=['status'])
    return campaign

@router.post('/{campaign_id}/resume/', response={200: CampaignOut, 400: ErrorWithCodeSchema})
def resume_campaign(request, campaign_id: int):

    campaign = get_object_or_404(Campaign, id=campaign_id, organization=request.auth.organization)
    if campaign.status != Campaign.Status.PAUSED:
        return 400, ErrorWithCodeSchema(detail='Campanha não está pausada', code='invalid_status')

    campaign.status = Campaign.Status.RUNNING
    campaign.save(update_fields=['status'])

    pending = list(CampaignContact.objects.filter(campaign=campaign, status='pending'))
    for i, cc in enumerate(pending):
        delay = i * random.uniform(campaign.interval_min, campaign.interval_max)
        send_campaign_message.apply_async(args=[cc.id], countdown=delay)

    return campaign

@router.post('/{campaign_id}/cancel/', response={200: CampaignOut, 400: ErrorWithCodeSchema})
def cancel_campaign(request, campaign_id: int):

    campaign = get_object_or_404(Campaign, id=campaign_id, organization=request.auth.organization)
    if campaign.status not in (Campaign.Status.RUNNING, Campaign.Status.PAUSED):
        return 400, ErrorWithCodeSchema(detail='Campanha não pode ser cancelada', code='invalid_status')

    campaign.status = Campaign.Status.CANCELLED
    campaign.save(update_fields=['status'])
    return campaign

#* ----- Contatos -----

@router.get('/{campaign_id}/contacts/', response=list[CampaignContactOut])
def list_campaign_contacts(request, campaign_id: int):
    campaign = get_object_or_404(Campaign, id=campaign_id, organization=request.auth.organization)
    return CampaignContact.objects.filter(campaign=campaign).select_related('contact').order_by('id')

@router.post('/{campaign_id}/contacts/', response={200: CampaignOut, 400: ErrorWithCodeSchema})
def add_contacts(request, campaign_id: int, data: AddContactsIn):

    campaign = get_object_or_404(Campaign, id=campaign_id, organization=request.auth.organization)
    if campaign.status != Campaign.Status.DRAFT:
        return 400, ErrorWithCodeSchema(detail='Só é possivel adicionar contatos em rascunho', code='not_draft')

    qs = Contact.objects.filter(organization=request.auth.organization)

    if data.add_all:
        contacts = qs
    else:
        q = Q()
        if data.contact_ids:
            q |= Q(id__in=data.contact_ids)
        if data.label_ids:
            q |= Q(labels__id__in=data.label_ids)
        contacts = qs.filter(q).distinct()

    added = 0
    for contact in contacts:
        _, created = CampaignContact.objects.get_or_create(
            campaign=campaign,
            contact=contact,
            defaults={'status': 'pending'}
        )
        if created:
            added += 1

    Campaign.objects.filter(id=campaign_id).update(
        total_contacts=CampaignContact.objects.filter(campaign=campaign).count()
    )
    campaign.refresh_from_db()
    return campaign

@router.delete('/{campaign_id}/contacts/{cc_id}/', response={204: None, 400: ErrorWithCodeSchema})
def remove_contact(request, campaign_id: int, cc_id: int):
    campaign = get_object_or_404(Campaign, id=campaign_id, organization=request.auth.organization)

    if campaign.status != Campaign.Status.DRAFT:
        return 400, ErrorWithCodeSchema(detail='Só é possivel remover contatos em rascunho', code='not_draft')

    cc = get_object_or_404(CampaignContact, id=cc_id, campaign=campaign, status='pending')
    cc.delete()
    Campaign.objects.filter(id=campaign_id).update(
        total_contacts=CampaignContact.objects.filter(campaign=campaign).count()
    )
    return 204, None
