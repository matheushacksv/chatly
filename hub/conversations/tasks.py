from agents.models import AgentDocument
from conversations.consumers import notify_new_message, notify_conversation_updated
from celery import shared_task
from integrations.services import send_message
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

@shared_task(soft_time_limit=90, time_limit=120)
def transcribe_and_process_message(attachment_id: int):
    from conversations.models import MessageAttachment, Message
    from conversations.transcription import transcribe_audio

    try: 
        attachment = MessageAttachment.objects.select_related(
        'message__conversation__agent__provider',
        'message__conversation__contact',
    ).get(id=attachment_id)
    except MessageAttachment.DoesNotExist:
        return

    try:
        transcription = transcribe_audio(attachment.file_url)
        attachment.transcription = transcription
        attachment.transcription_status = 'done'
        attachment.save()

    except Exception as e:
        attachment.transcription_status = 'failed'
        attachment.save()
        from conversations.consumers import notify_attachment_updated
        notify_attachment_updated(attachment.message.conversation_id, attachment)
        return

    conversation = attachment.message.conversation

    from conversations.consumers import notify_attachment_updated
    notify_attachment_updated(conversation.id, attachment)


    if not conversation.agent or not conversation.ai_active:
        return

    history = list(
        conversation.messages.order_by('-created_at').values('role', 'content')[:50]
    )
    history.reverse()

    if history:
        history[-1]['content'] = f'[Audio]: {transcription}'

    try:
        response_text = _call_agno(conversation.agent, history)
    except Exception as e:
        logger.error(f'[transcribe_and_process_message] Erro no agno: {e}')
        return

    message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=response_text,
    )

    from conversations.consumers import notify_new_message
    notify_new_message(conversation.id, message)

    try:
        instance = conversation.agent.whatsapp_instance
        send_message(
            instance_api_key=instance.instance_api_key,
            phone=conversation.contact.phone,
            text=response_text
        )
    except Exception as e:
        logger.error(f'[transcribe_and_process_message] Erro ao enviar mensagem: {e}')

@shared_task(soft_time_limit=30, time_limit=60)
def send_scheduled_message(message_id: int):
    from conversations.models import Message
    from integrations.services import send_message

    try:
        message = Message.objects.select_related(
            'conversation__agent__whatsapp_instance', 'conversation__contact'
        ).get(id=message_id)

        instance = message.conversation.agent.whatsapp_instance if message.conversation.agent else None
        if not instance:
            from integrations.models import WhatsAppInstance
            instance = WhatsAppInstance.objects.filter(
                organization=message.conversation.organization_id,
                status=WhatsAppInstance.Status.CONNECTED
            ).first()
        phone = message.conversation.contact.phone

        send_message(instance_api_key=instance.instance_api_key, phone=phone, text=message.content)

        message.scheduled_status = 'sent'
        message.save(update_fields=['scheduled_status'])

        notify_new_message(message.conversation_id, message)
    
    except Exception as e:
        logger.error(f'[send_scheduled_message] Falha ao enviar mensagem {message_id}: {e}')
        Message.objects.filter(id=message_id).update(scheduled_status='failed')

@shared_task(soft_time_limit=90, time_limit=120)
def process_message(message_id: int):
    from conversations.models import Message, Conversation
    from agents.models import AIAgent

    try:
        message = Message.objects.select_related('conversation__agent__provider').get(id=message_id)
    except Message.DoesNotExist:
        return
    
    conversation = message.conversation

    if not conversation.agent:
        return

    if not conversation.ai_active:
        return

    history = list(
        conversation.messages.order_by('-created_at').values('role', 'content')[:50]
    )
    history.reverse()

    attachments = list(message.attachments.all())

    from django.utils import timezone
    from datetime import timedelta

    Conversation.objects.filter(id=conversation.id).update(
        follow_up_count=0,
        next_follow_up_at=None
    )
    conversation.refresh_from_db(fields=['follow_up_count', 'next_follow_up_at'])

    try:
        response_text = _call_agno(conversation.agent, history, attachments=attachments)
    except Exception as e:
        logger.error(f'[process_message] Erro no agno: {e}')
        return

    if not response_text:
        logger.warning('[process_message] Agno retornou response text vazio')
        return

    assistant_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=response_text
    )

    if conversation.agent and conversation.agent.follow_up_enabled:
        Conversation.objects.filter(id=conversation.id).update(
            next_follow_up_at=timezone.now() + timedelta(minutes=conversation.agent.follow_up_delay)
        )

    notify_new_message(conversation.id, assistant_message)

    try:
        instance = conversation.agent.whatsapp_instance
    except Exception as e:
        logger.error(f'[process_message] Erro ao obter instância: {e}')
        return

    send_message(instance_api_key=instance.instance_api_key, phone=conversation.contact.phone, text=response_text)

    return 200

def _call_agno(agent_config, history, attachments=None):
    from agno.agent import Agent
    from agno.models.message import Message as AgnoMessage
    from agno.media import Image

    model = _get_agno_model(agent_config)
    provider_type = agent_config.provider.provider_type

    rag_context = ''
    docs = AgentDocument.objects.filter(agent=agent_config, status='ready')
    if docs.exists():
        chunks = '\n\n---\n\n'.join(d.content[:5000] for d in docs)
        rag_context = f'\n\n## Base de conhecimento\n{chunks}'

    system = agent_config.system_prompt + rag_context

    from agents.tool_factory import get_tools_for_agent
    tools = get_tools_for_agent(agent_config)

    agent = Agent(
        model=model,
        instructions=system,
        tools=tools or None
    )

    all_messages = [
        AgnoMessage(role=m['role'], content=m['content'])
        for m in history
        if m['role'] in ('user', 'assistant')
    ]

    images = []
    if attachments and provider_type in ('openai', 'anthropic'):
        for attachment in attachments:
            if attachment.media_type == 'image':
                images.append(Image(url=attachment.file_url))

    kwargs = {}
    if images:
        kwargs['images'] = images

    response = agent.run(all_messages, **kwargs)
    return response.content

def _get_agno_model(agent_config):
    from agno.models.openai import OpenAIChat
    from agno.models.anthropic import Claude
    from agno.models.groq import Groq

    provider = agent_config.provider
    api_key = provider.api_key
    model_name = agent_config.model_name

    if provider.provider_type == 'openai':
        return OpenAIChat(id=model_name, api_key=api_key)
    elif provider.provider_type == 'anthropic':
        return Claude(id=model_name, api_key=api_key)
    elif provider.provider_type == 'groq':
        return Groq(id=model_name, api_key=api_key)
    else:
        raise ValueError(f'Provider not supported: {provider.provider_type}')
    
@shared_task(soft_time_limit=120, time_limit=180)
def check_follow_ups():
    from django.utils import timezone
    from conversations.models import Conversation

    now = timezone.now()
    convs = Conversation.objects.filter(
        status='open',
        ai_active=True,
        next_follow_up_at__lte=now,
        next_follow_up_at__isnull=False,
        agent__follow_up_enabled=True
    ).select_related('agent', 'organization')

    for conv in convs:
        if conv.follow_up_count >= conv.agent.max_follow_ups:
            Conversation.objects.filter(id=conv.id).update(next_follow_up_at=None)
            continue
        if conv.agent.follow_up_respect_hours:
            current_time = timezone.now()
            next_window = next_available_window(conv.organization, current_time)
            if next_window is None or next_window > current_time:
                new_time = next_window or (current_time + timedelta(hours=1))
                Conversation.objects.filter(id=conv.id).update(next_follow_up_at=new_time)
                continue
        send_follow_up.delay(conv.id)

@shared_task(soft_time_limit=90, time_limit=120)
def send_follow_up(conversation_id: int):
    from django.utils import timezone
    from conversations.models import Conversation, Message

    try:
        conv = Conversation.objects.select_related(
            'agent__provider', 'agent__whatsapp_instance', 'contact'
        ).get(id=conversation_id)
    except Conversation.DoesNotExist:
        return

    if conv.status != 'open' or not conv.ai_active or not conv.agent:
        return
    if not conv.agent.follow_up_enabled:
        return
    if conv.follow_up_count >= conv.agent.max_follow_ups:
        Conversation.objects.filter(id=conversation_id).update(next_follow_up_at=None)
        return
    
    history = list(conv.messages.order_by('-created_at').values('role', 'content')[:50])
    history.reverse()

    extra = conv.agent.follow_up_prompt or 'O usuário não respondeu. Envie uma mensagem de follow-up para retomar a conversa.'
    original_prompt = conv.agent.system_prompt
    conv.agent.system_prompt = f'{original_prompt}\n\n[FOLLOW-UP {conv.follow_up_count + 1}/{conv.agent.max_follow_ups}]: {extra}'

    try:
        response_text = _call_agno(conv.agent, history)
    except Exception as e:
        logger.error(f'[send_follow_up] Erro no agno {e}')
        return
    finally:
        conv.agent.system_prompt = original_prompt

    if not response_text:
        return

    message = Message.objects.create(
        conversation=conv,
        role=Message.Role.ASSISTANT,
        content=response_text
    )

    notify_new_message(conv.id, message)

    try:
        instance = conv.agent.whatsapp_instance
        send_message(instance_api_key=instance.instance_api_key, phone=conv.contact.phone, text=response_text)
    except Exception as e:
        logger.error(f'[send_follow_up] Erro ao enviar WA: {e}')

    now = timezone.now()
    Conversation.objects.filter(id=conversation_id).update(
        follow_up_count=conv.follow_up_count + 1,
        next_follow_up_at=now + timedelta(minutes=conv.agent.follow_up_delay)
    )
    conv.refresh_from_db(fields=['follow_up_count', 'next_follow_up_at'])
    notify_conversation_updated(conv)

def next_available_window(organization, from_dt):
    from accounts.models import BusinessHours
    from datetime import timedelta
    from django.utils import timezone

    hours = list(BusinessHours.objects.filter(organization=organization).order_by('weekday'))
    if not hours:
        return from_dt

    bh_map = {bh.weekday: bh for bh in hours}
    # Comparar em hora local para bater com os horários cadastrados
    current = timezone.localtime(from_dt)
    for _ in range(8):
        wd = current.weekday()
        bh = bh_map.get(wd)
        if bh and bh.is_open:
            open_dt = current.replace(hour=bh.open_time.hour, minute=bh.open_time.minute, second=0, microsecond=0)
            close_dt = current.replace(hour=bh.close_time.hour, minute=bh.close_time.minute, second=0, microsecond=0)
            if open_dt <= current < close_dt:
                return from_dt
            if current < open_dt:
                return open_dt.astimezone(timezone.utc)
        current = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return None
