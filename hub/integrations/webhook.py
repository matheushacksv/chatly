from integrations.models import PipedriveIntegration
from conversations.consumers import notify_new_message, notify_new_conversation, notify_conversation_list_updated
from ninja import Router
from django.http import HttpRequest
from .models import WhatsAppInstance
from contacts.models import Contact
from conversations.models import Conversation, Message
from conversations.tasks import process_message
from .schemas import WebhookPayload
from conversations.utils.utils import upload_attachment
from conversations.models import MessageAttachment
from integrations.pipedrive_tasks import create_deal_from_conversation, sync_contact_to_pipedrive
from . import services

router = Router(tags=['Webhooks'])

def _register_webhook(instance, services):
    from django.conf import settings
    webhook_url = f'{settings.BASE_URL}/api/webhooks/whatsapp/{instance.instance_name}/'
    try:
        services.connect_instance(instance_api_key=instance.instance_api_key, webhook_url=webhook_url)
    except Exception:
        pass

@router.post('/{instance_name}/', auth=None)
def whatsapp_webhook(request: HttpRequest, instance_name: str, payload: WebhookPayload):
    event = payload.event
    data = payload.data or  {}

    
    if event == 'PairSuccess':
        try:
            instance = WhatsAppInstance.objects.get(instance_name=instance_name)
            jid = data.get('jid', '') if isinstance(data, dict) else ''
            phone = jid.split(':')[0].split('@')[0]
            if phone:
                instance.phone_number = phone
            instance.status = WhatsAppInstance.Status.CONNECTED
            instance.save()
            _register_webhook(instance, services)
        except WhatsAppInstance.DoesNotExist:
            pass
        return {'status': 'ok'}

    if event == 'Connected':
        try:
            instance = WhatsAppInstance.objects.get(instance_name=instance_name)
            instance.status = WhatsAppInstance.Status.CONNECTED
            instance.save()
            _register_webhook(instance, services)
        except WhatsAppInstance.DoesNotExist:
            pass
        return {'status': 'ok'}                                                                                                                                          
                                                                                                                                                                       
    if event == 'LoggedOut':                                                                                                                                             
        try:                                                                                                                                                           
            instance = WhatsAppInstance.objects.get(instance_name=instance_name)
            instance.status = WhatsAppInstance.Status.DISCONNECTED                                                                                                       
            instance.save()                                                                                                                                              
        except WhatsAppInstance.DoesNotExist:                                                                                                                            
            pass                                                                                                                                                         
        return {'status': 'ok'}   

    if event != 'Message':
        return {'status': 'ignored'} #####! Ignorando tudo que não é mensagem
    

    info = data.get('Info', {}) if isinstance(data, dict) else ''

    if info.get('IsFromMe') or info.get('IsGroup'):
        return {'status': 'ignored'} #####! Ignorando fromMe e Group

    from core.utils.phone import normalize_phone

    sender_raw = info.get('Sender', '').split('@')[0]
    sender = normalize_phone(sender_raw)
    push_name = info.get('PushName', '')
    msg_obj = data.get('Message', {}) or {}
    text = (
        msg_obj.get('conversation')
        or (msg_obj.get('extendedTextMessage') or {}).get('text')
        or (msg_obj.get('imageMessage') or {}).get('caption')
        or (msg_obj.get('videoMessage') or {}).get('caption')
        or ''
    )

    if not text and info.get('Type') != 'media':
        return {'status': 'ignored'}

    try:
        instance = WhatsAppInstance.objects.select_related('agent__organization').get(instance_name=instance_name)
    except WhatsAppInstance.DoesNotExist:
        return {'status': 'instance_not_found'}

    organization = instance.organization

    contact, created = Contact.objects.get_or_create(
        organization=organization,
        phone=sender,
        defaults={'name': push_name},
    )

    if created:
        if PipedriveIntegration.objects.filter(organization=organization, is_active=True).exists():
            sync_contact_to_pipedrive.delay(contact.id)
        from automations.events import trigger_event
        trigger_event('contact.created', organization.id, contact_id=contact.id)

    from django.db.models import Max

    conversation = (
        Conversation.objects.filter(
            organization=organization,
            contact=contact,
            status=Conversation.Status.OPEN,
        )
        .annotate(last_msg_at=Max('messages__created_at'))
        .order_by('-last_msg_at', '-started_at')
        .first()
    )

    is_new_conversation = False
    if not conversation:
        conversation = Conversation.objects.create(
            organization=organization,
            contact=contact,
            status=Conversation.Status.OPEN,
            agent=instance.agent,
            instance=instance,
        )
        is_new_conversation = True
        from django.contrib.contenttypes.models import ContentType
        from integrations.models import AssignmentQueue
        from integrations.services import assign_from_queue
        ct = ContentType.objects.get_for_model(WhatsAppInstance)
        try:
            queue = AssignmentQueue.objects.prefetch_related('members__user').get(
                content_type=ct, object_id=instance.id, is_active=True
            )
            assign_from_queue(queue, conversation)
        except AssignmentQueue.DoesNotExist:
            pass
        if PipedriveIntegration.objects.filter(organization=organization, is_active=True).exists():
            create_deal_from_conversation.delay(conversation.id)
        from automations.events import trigger_event
        trigger_event(
            'conversation.created', organization.id,
            conversation_id=conversation.id, contact_id=contact.id,
        )
    else:
        update_fields = []
        if not conversation.agent and instance.agent:
            conversation.agent = instance.agent
            update_fields.append('agent')
            if not conversation.ai_active:
                conversation.ai_active = True
                update_fields.append('ai_active')
        if not conversation.instance_id:
            conversation.instance = instance
            update_fields.append('instance')
        if update_fields:
            conversation.save(update_fields=update_fields)

    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=text
    )

    from automations.events import trigger_event
    trigger_event(
        'message.received', organization.id,
        message_id=message.id, conversation_id=conversation.id, contact_id=contact.id,
    )

    if info.get('Type') == 'media':
        from conversations.models import MessageAttachment
        from conversations.utils.utils import upload_attachment
        from conversations.tasks import transcribe_and_process_message

        msg_data = data.get('Message', {})
        base64_data = msg_data.get('base64', '')
        media_subtype = info.get('MediaType', '')

        mime_type_map = {
            'image': 'image/jpeg',
            'audio': 'audio/ogg',
            'ptt': 'audio/ogg',
            'video': 'video/mp4',
            'document': 'application/octet-stream',
            'sticker': 'image/webp',
            'gif': 'image/gif'
        }

        mime = mime_type_map.get(media_subtype, 'application/octet-stream')

        # ptt (push-to-talk) é áudio de voz — normaliza para 'audio'
        stored_media_type = 'audio' if media_subtype == 'ptt' else media_subtype

        if base64_data:
            try:
                url = upload_attachment(base64_data, mime)
                attachment = MessageAttachment.objects.create(
                    message=message,
                    media_type=stored_media_type,
                    file_url=url,
                    mime_type=mime,
                )
                if media_subtype in ('audio', 'ptt'):
                    transcribe_and_process_message.delay(attachment.id)
                elif instance.agent and conversation.ai_active:
                    process_message.delay(message.id)

            except Exception as e:
                print(f'Erro ao salvar a midia: {e}')

    else:
        if instance.agent and conversation.ai_active:
            process_message.delay(message.id)

    # Notifica após o attachment estar criado, para que a serialização inclua os anexos
    notify_new_message(conversation.id, message)

    # Notifica a lista de conversas da organização em tempo real
    conversation.contact = contact  # garante que o objeto está em memória
    if is_new_conversation:
        notify_new_conversation(conversation)
    else:
        notify_conversation_list_updated(conversation)

    return {'status': 'ok'}