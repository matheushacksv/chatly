from integrations.models import PipedriveIntegration
from integrations.schemas import MoveStageIn
from accounts.utils import has_permission, is_owner_or_admin
from labels.schemas import SetLabelsIn
from contacts.models import Contact
from integrations.models import WhatsAppInstance
from ninja import Router, Query, File, Form
from django.db.models import OuterRef, Subquery
from .consumers import notify_new_conversation, notify_conversation_list_updated
from ninja.files import UploadedFile
from typing import Optional
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .tasks import send_scheduled_message, send_whatsapp_message
from integrations.pipedrive_tasks import close_deal_from_conversation
import uuid
from templates.models import MessageTemplate
from .models import Conversation, Message, MessageAttachment, Sticker
from .schemas import ConversationOut, MessageOut, UpdateConversationIn, SendMessageIn, StickerOut, SendStickerIn, StartConversationIn
from core.utils.errors import ErrorWithCodeSchema, GenericErrorSchema
from integrations.services import send_message, send_media, send_sticker
from django.shortcuts import get_object_or_404
import logging

logger = logging.getLogger(__name__)

router = Router(tags=['Conversations'])

ALLOWED_MEDIA_TYPES = {'image', 'audio', 'document', 'video', 'sticker'}

def _get_instance(conversation, override_instance_id, organization):
    if override_instance_id:
        return WhatsAppInstance.objects.filter(id=override_instance_id, organization=organization).first()
    if conversation.instance_id:
        return conversation.instance
    if conversation.agent_id and conversation.agent:
        return conversation.agent.whatsapp_instance
    return WhatsAppInstance.objects.filter(organization=organization, status=WhatsAppInstance.Status.CONNECTED).first()


# ------------------------------------------------------------------ #
# Rotas ESTÁTICAS                                                    #
# ------------------------------------------------------------------ #

@router.get('/', response=list[ConversationOut])
def list_conversations(
    request,
    status: Optional[str] = Query(None),
    agent_id: Optional[int] = Query(None),
    assigned_to_id: Optional[int] = Query(None),
    contact_id: Optional[int] = Query(None),
    label_id: Optional[int] = Query(None),
    instance_id: Optional[int] = Query(None),
    limit: int = Query(200),
    offset: int = Query(0),
):
    from accounts.models import User

    user = request.auth
    qs = Conversation.objects.filter(organization=user.organization).select_related('contact', 'agent', 'assigned_to', 'instance')

    if user.role == User.Role.MEMBER:
        can_view_all = (
            user.permission_group is not None
            and user.permission_group.can_view_conversations
        )
        if not can_view_all:
            qs = qs.filter(assigned_to=user)

    if status:
        qs = qs.filter(status=status)
    if agent_id:
        qs = qs.filter(agent_id=agent_id)
    if assigned_to_id:
        qs = qs.filter(assigned_to_id=assigned_to_id)
    if contact_id:
        qs = qs.filter(contact_id=contact_id)
    if label_id:
        qs = qs.filter(label_id=label_id)
    if instance_id:
        qs = qs.filter(instance_id=instance_id)

    last_msg = Message.objects.filter(conversation=OuterRef('pk')).order_by('-created_at')
    qs = qs.annotate(
        _last_msg_id=Subquery(last_msg.values('id')[:1]),
        _last_msg_role=Subquery(last_msg.values('role')[:1]),
        _last_msg_content=Subquery(last_msg.values('content')[:1]),
        _last_msg_created_at=Subquery(last_msg.values('created_at')[:1]),
    )
    return list(qs.order_by('-started_at').prefetch_related('labels')[offset:offset + limit])


@router.post('/start/', response={201: ConversationOut, 400: ErrorWithCodeSchema})
def start_conversation(request, data: StartConversationIn):
    try:
        instance = WhatsAppInstance.objects.get(id=data.instance_id, organization=request.auth.organization)
    except WhatsAppInstance.DoesNotExist:
        return 400, ErrorWithCodeSchema(detail='Instance not found', code='instance_not_found')

    from core.utils.phone import normalize_phone
    phone = normalize_phone(data.phone)

    contact, created = Contact.objects.get_or_create(
        organization=request.auth.organization,
        phone=phone,
        defaults={
            'name': data.name or phone,
            'email': data.email or '',
            'pipedrive_person_id': data.pipedrive_person_id,
        },
    )
    if not created:
        updates = []
        if data.name:
            contact.name = data.name
            updates.append('name')
        if data.email and not contact.email:
            contact.email = data.email
            updates.append('email')
        if data.pipedrive_person_id and not contact.pipedrive_person_id:
            contact.pipedrive_person_id = data.pipedrive_person_id
            updates.append('pipedrive_person_id')
        if updates:
            contact.save(update_fields=updates)

    from agents.models import AIAgent
    agent = None
    if data.agent_id:
        try:
            agent = AIAgent.objects.get(id=data.agent_id, organization=request.auth.organization)
        except AIAgent.DoesNotExist:
            pass

    # Garante apenas uma conversa aberta por contato
    open_convs = Conversation.objects.filter(
        organization=request.auth.organization,
        contact=contact,
        status=Conversation.Status.OPEN,
    ).order_by('-started_at')

    conversation = open_convs.first()
    if conversation:
        open_convs.exclude(pk=conversation.pk).update(status=Conversation.Status.CLOSED)
        if not conversation.instance_id:
            conversation.instance = instance
            conversation.save(update_fields=['instance'])
    else:
        conversation = Conversation.objects.create(
            organization=request.auth.organization,
            contact=contact,
            status=Conversation.Status.OPEN,
            agent=agent or instance.agent,
            instance=instance
        )

    if data.message:
        from integrations.services import send_message as _send

        Message.objects.create(conversation=conversation, role=Message.Role.OPERATOR, content=data.message, sent_by=request.auth)

        try:
            _send(instance_api_key=instance.instance_api_key, phone=contact.phone, text=data.message)
        except Exception as e:
            logger.error(f'Erro ao enviar mensagem: {e}')

    conversation.contact = contact
    notify_new_conversation(conversation)

    return 201, conversation


# ------ Sticker library ------

@router.get('/stickers', response=list[StickerOut])
def list_stickers(request):
    return Sticker.objects.filter(organization=request.auth.organization).order_by('-created_at')


@router.post('/stickers', response={201: StickerOut, 400: ErrorWithCodeSchema})
def upload_sticker(
    request,
    file: UploadedFile = File(...),
    name: str = Form(''),
):
    mime_type = file.content_type or 'image/webp'
    extension = mime_type.split('/')[-1].split(';')[0]
    file_name = f'stickers/{uuid.uuid4()}.{extension}'
    saved_path = default_storage.save(file_name, ContentFile(file.read()))
    file_url = default_storage.url(saved_path)

    sticker = Sticker.objects.create(
        organization=request.auth.organization,
        name=name or file.name,
        file_url=file_url,
        created_by=request.auth,
    )
    return 201, sticker


@router.post('/stickers/from-attachment/{attachment_id}', response={201: StickerOut, 404: ErrorWithCodeSchema, 400: ErrorWithCodeSchema})
def save_sticker_from_attachment(request, attachment_id: int, name: str = ''):
    try:
        attachment = MessageAttachment.objects.select_related(
            'message__conversation'
        ).get(
            id=attachment_id,
            media_type=MessageAttachment.MediaType.STICKER,
            message__conversation__organization=request.auth.organization,
        )
    except MessageAttachment.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Sticker attachment not found', code='not_found')

    sticker = Sticker.objects.create(
        organization=request.auth.organization,
        name=name,
        file_url=attachment.file_url,
        created_by=request.auth,
    )
    return 201, sticker


@router.delete('/stickers/{sticker_id}', response={204: None, 404: ErrorWithCodeSchema})
def delete_sticker(request, sticker_id: int):
    try:
        sticker = Sticker.objects.get(id=sticker_id, organization=request.auth.organization)
    except Sticker.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Sticker not found', code='sticker_not_found')

    sticker.delete()
    return 204, None


#* ------------------------------------------------------------------ #
#* Rotas DINÂMICAS                                                    #
#* ------------------------------------------------------------------ #

@router.patch('/{conversation_id}', response={200: ConversationOut, 400: ErrorWithCodeSchema})
def update_conversation(request, conversation_id: int, data: UpdateConversationIn):
    try:
        conversation = Conversation.objects.select_related('contact', 'agent', 'assigned_to').get(id=conversation_id, organization=request.auth.organization)
    except Conversation.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Conversation not found', code='conversation_not_found')

    triggered_close = False
    if data.status is not None:
        if data.status == Conversation.Status.CLOSED and conversation.status != Conversation.Status.CLOSED:
            conversation.ended_at = timezone.now()
            triggered_close = True
            if PipedriveIntegration.objects.filter(organization=request.auth.organization, is_active=True).exists():
                close_deal_from_conversation.delay(conversation.id)
        conversation.status = data.status
    if data.agent_id is not None:
        if data.agent_id == 0:
            conversation.agent = None
        else:
            from agents.models import AIAgent
            agent = AIAgent.objects.filter(id=data.agent_id, organization=request.auth.organization).first()
            if agent is None:
                return 400, ErrorWithCodeSchema(detail='Agente inválido', code='invalid_agent')
            conversation.agent = agent
    if data.ai_active is not None:
        conversation.ai_active = data.ai_active
    if data.assigned_to_id is not None:
        conversation.assigned_to_id = data.assigned_to_id

    conversation.save()
    notify_conversation_list_updated(conversation)

    if triggered_close:
        from automations.events import trigger_event
        trigger_event(
            'conversation.closed',
            request.auth.organization_id,
            conversation_id=conversation.id,
            contact_id=conversation.contact_id,
        )

    return conversation

@router.post('/{conversation_id}/labels', response={200: ConversationOut})
def set_conversation_labels(request, conversation_id: int, data: SetLabelsIn):
    conversation = get_object_or_404(Conversation, id=conversation_id, organization=request.auth.organization)
    conversation.labels.set(data.label_ids)
    conversation.contact.labels.set(data.label_ids)
    return conversation

@router.delete('/{conversation_id}', response={204: None, 403: ErrorWithCodeSchema})
def delete_conversation(request, conversation_id: int):
    if not has_permission(request.auth, 'can_delete_conversations'):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    conversation = get_object_or_404(Conversation, id=conversation_id, organization=request.auth.organization)

    conversation.delete()

    return 204, None


@router.get('/{conversation_id}/messages', response={200: list[MessageOut], 404: ErrorWithCodeSchema})
def list_messages(request, conversation_id: int, limit: int = Query(50), before_id: Optional[int] = Query(None)):
    try:
        conversation = Conversation.objects.get(id=conversation_id, organization=request.auth.organization)
    except Conversation.DoesNotExist:
        return 400, ErrorWithCodeSchema(detail='Conversation not found', code='conversation_not_found')

    qs = conversation.messages.select_related('sent_by').prefetch_related('attachments')
    if before_id is not None:
        qs = qs.filter(id__lt=before_id)
    msgs = list(qs.order_by('-created_at')[:max(1, limit)])
    msgs.reverse()
    return msgs


@router.post('/{conversation_id}/messages', response={201: MessageOut, 404: GenericErrorSchema, 400: ErrorWithCodeSchema})
def user_send_message(request, conversation_id: int, data: SendMessageIn, instance_id: Optional[int] = Query(None)):
    try:
        conversation = Conversation.objects.select_related(
            'contact', 'agent__whatsapp_instance', 'instance'
        ).get(id=conversation_id, organization=request.auth.organization)
    except Conversation.DoesNotExist:
        return 404, {'detail': 'Conversation not found'}

    if conversation.ai_active:
        conversation.ai_active = False
        conversation.save(update_fields=['ai_active'])

    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.OPERATOR,
        content=data.content,
        sent_by=request.auth,
        scheduled_at=data.scheduled_at or None,
        scheduled_status='pending' if data.scheduled_at else None,
    )

    from conversations.consumers import notify_new_message
    notify_new_message(conversation.id, message)

    if data.scheduled_at:
        send_scheduled_message.apply_async(args=[message.id], eta=data.scheduled_at)
    else:
        send_whatsapp_message.delay(message.id, instance_id)

    return 201, message
        
    

@router.post('/{conversation_id}/messages/media', response={201: MessageOut, 404: GenericErrorSchema, 400: ErrorWithCodeSchema})
def user_send_media(
    request,
    conversation_id: int,
    file: UploadedFile = File(...),
    caption: str = Form(''),
    media_type: str = Form('image'),
    instance_id: Optional[int] = Query(None),
):
    if media_type not in ALLOWED_MEDIA_TYPES:
        return 400, ErrorWithCodeSchema(detail='Invalid media_type', code='invalid_media_type')

    try:
        conversation = Conversation.objects.select_related(
            'contact', 'agent__whatsapp_instance', 'instance'
        ).get(id=conversation_id, organization=request.auth.organization)
    except Conversation.DoesNotExist:
        return 404, {'detail': 'Conversation not found'}

    if conversation.ai_active:
        conversation.ai_active = False
        conversation.save(update_fields=['ai_active'])

    mime_type = file.content_type or 'application/octet-stream'
    extension = mime_type.split('/')[-1].split(';')[0]
    file_name = f'attachments/{uuid.uuid4()}.{extension}'
    saved_path = default_storage.save(file_name, ContentFile(file.read()))
    file_url = default_storage.url(saved_path)

    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.OPERATOR,
        content=caption,
        sent_by=request.auth,
    )

    MessageAttachment.objects.create(
        message=message,
        media_type=media_type,
        file_url=file_url,
        file_name=file.name,
        mime_type=mime_type,
        transcription_status='done',
    )

    from conversations.consumers import notify_new_message
    notify_new_message(conversation.id, message)

    try:
        instance = _get_instance(conversation, instance_id, request.auth.organization)
        if instance:
            if media_type == 'sticker':
                send_sticker(
                    instance_api_key=instance.instance_api_key,
                    phone=conversation.contact.phone,
                    sticker_url=file_url,
                )
            else:
                send_media(
                    instance_api_key=instance.instance_api_key,
                    phone=conversation.contact.phone,
                    media_url=file_url,
                    media_type=media_type,
                    mime_type=mime_type,
                    caption=caption,
                )
    except Exception as e:
        logger.error(f'Erro ao enviar mídia: {e}')

    return 201, message


@router.post('/{conversation_id}/messages/sticker', response={201: MessageOut, 404: GenericErrorSchema, 400: ErrorWithCodeSchema})
def send_sticker_from_library(request, conversation_id: int, data: SendStickerIn, instance_id: Optional[int] = Query(None)):
    try:
        conversation = Conversation.objects.select_related(
            'contact', 'agent__whatsapp_instance', 'instance'
        ).get(id=conversation_id, organization=request.auth.organization)
    except Conversation.DoesNotExist:
        return 404, {'detail': 'Conversation not found'}

    try:
        sticker = Sticker.objects.get(id=data.sticker_id, organization=request.auth.organization)
    except Sticker.DoesNotExist:
        return 400, ErrorWithCodeSchema(detail='Sticker not found', code='sticker_not_found')

    if conversation.ai_active:
        conversation.ai_active = False
        conversation.save(update_fields=['ai_active'])

    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.OPERATOR,
        content='',
        sent_by=request.auth,
    )

    MessageAttachment.objects.create(
        message=message,
        media_type=MessageAttachment.MediaType.STICKER,
        file_url=sticker.file_url,
        mime_type='image/webp',
        transcription_status='done',
    )

    from conversations.consumers import notify_new_message
    notify_new_message(conversation.id, message)

    try:
        instance = _get_instance(conversation, instance_id, request.auth.organization)
        if instance:
            send_sticker(
                instance_api_key=instance.instance_api_key,
                phone=conversation.contact.phone,
                sticker_url=sticker.file_url,
            )
    except Exception as e:
        logger.error(f'Erro ao enviar figurinha: {e}')

    return 201, message

@router.post('/{conversation_id}/clear-memory', response={200: ConversationOut, 403: ErrorWithCodeSchema})
def clear_ai_memory(request, conversation_id: int):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')
    
    conversation = get_object_or_404(Conversation, id=conversation_id, organization=request.auth.organization)
    conversation.memory_reset_at = timezone.now()
    conversation.save(update_fields=['memory_reset_at'])
    return conversation

# ------------------------------------------------------------------ #
# Pipedrive                                                          #
# ------------------------------------------------------------------ #

@router.get('/{conversation_id}/pipedrive')
def get_conversation_pipedrive(request, conversation_id: int):
    from django.core.cache import cache
    from integrations.pipedrive_services import get_deal, pipeline_with_stages, get_activities

    conv = get_object_or_404(Conversation, id=conversation_id, organization=request.auth.organization)
    if not conv.pipedrive_deal_id:
        return {'deal': None, 'stages': [], 'activities': []}

    integration = PipedriveIntegration.objects.filter(
        organization=request.auth.organization, is_active=True
    ).first()
    if not integration:
        return {'deal': None, 'stages': [], 'activities': []}

    cache_key = f'pipedrive_deal_{conv.pipedrive_deal_id}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    deal = get_deal(integration.api_key, conv.pipedrive_deal_id)
    activities = get_activities(integration.api_key, conv.pipedrive_deal_id)

    pipeline_stages = []
    if deal:
        for p in pipeline_with_stages(integration.api_key):
            if p['id'] == deal.get('pipeline_id'):
                pipeline_stages = p['stages']
                break

    result = {'deal': deal, 'stages': pipeline_stages, 'activities': activities}
    cache.set(cache_key, result, timeout=60)
    return result


@router.patch('/{conversation_id}/pipedrive/stage')
def move_deal_stage(request, conversation_id: int, data: MoveStageIn):
    from django.core.cache import cache
    from integrations.pipedrive_services import update_deal_stage

    conv = get_object_or_404(Conversation, id=conversation_id, organization=request.auth.organization)
    if not conv.pipedrive_deal_id:
        return {'ok': False}

    integration = PipedriveIntegration.objects.filter(
        organization=request.auth.organization, is_active=True
    ).first()
    if not integration:
        return {'ok': False}

    ok = update_deal_stage(integration.api_key, conv.pipedrive_deal_id, data.stage_id)
    if ok:
        cache.delete(f'pipedrive_deal_{conv.pipedrive_deal_id}')
    return {'ok': ok}


@router.post('/{conversation_id}/pipedrive/activities/{activity_id}/done')
def complete_activity(request, conversation_id: int, activity_id: int):
    from django.core.cache import cache
    from integrations.pipedrive_services import mark_activity_done

    conv = get_object_or_404(Conversation, id=conversation_id, organization=request.auth.organization)
    if not conv.pipedrive_deal_id:
        return {'ok': False}

    integration = PipedriveIntegration.objects.filter(
        organization=request.auth.organization, is_active=True
    ).first()
    if not integration:
        return {'ok': False}

    ok = mark_activity_done(integration.api_key, activity_id)
    if ok:
        cache.delete(f'pipedrive_deal_{conv.pipedrive_deal_id}')
    return {'ok': ok}


@router.post('/{conversation_id}/messages/from-template', response={201: MessageOut, 404: GenericErrorSchema})
def send_from_template(request, conversation_id: int, template_id: int, instance_id: Optional[int] = Query(None)):
    # Busca conversa
    try:
        conversation = Conversation.objects.select_related(
            'contact', 'agent__whatsapp_instance', 'instance'
        ).get(id=conversation_id, organization=request.auth.organization)
    except Conversation.DoesNotExist:
        return 404, {'detail': 'Conversation not found'}

    # Busca template
    try:
        template = MessageTemplate.objects.get(id=template_id, organization=request.auth.organization)
    except MessageTemplate.DoesNotExist:
        return 404, {'detail': 'Template not found'}

    # Desativa IA ao enviar manualmente
    if conversation.ai_active:
        conversation.ai_active = False
        conversation.save(update_fields=['ai_active'])

    # Cria a mensagem
    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.OPERATOR,
        content=template.content,
        sent_by=request.auth,
    )

    # Se tiver mídia, cria o attachment
    if template.media_type != 'text' and template.file_url:
        MessageAttachment.objects.create(
            message=message,
            media_type=template.media_type,
            file_url=template.file_url,
            mime_type=template.mime_type,
            transcription_status='done',
        )

    # Notifica via WebSocket (tempo real para outros operadores no chat)
    from conversations.consumers import notify_new_message
    notify_new_message(conversation.id, message)

    # Envia via WhatsApp
    try:
        instance = _get_instance(conversation, instance_id, request.auth.organization)

        if instance:
            if template.media_type == 'text':
                send_message(
                    instance_api_key=instance.instance_api_key,
                    phone=conversation.contact.phone,
                    text=template.content,
                )
            elif template.media_type == 'sticker':
                send_sticker(
                    instance_api_key=instance.instance_api_key,
                    phone=conversation.contact.phone,
                    sticker_url=template.file_url,
                )
            else:
                send_media(
                    instance_api_key=instance.instance_api_key,
                    phone=conversation.contact.phone,
                    media_url=template.file_url,
                    media_type=template.media_type,
                    mime_type=template.mime_type,
                    caption=template.content,
                )
    except Exception as e:
        logger.error(f'Erro ao enviar template via WhatsApp: {e}')

    return 201, message



