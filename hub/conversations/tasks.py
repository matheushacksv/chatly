from agents.models import AgentDocument
from conversations.consumers import notify_new_message, notify_conversation_updated
from celery import shared_task
from integrations.services import send_message
import logging
from datetime import timedelta
import uuid
from django.core.cache import cache
import re

logger = logging.getLogger(__name__)
ACCUMULATE_MARKER_KEY = 'accumulate:marker:{conv_id}'
_RETRY_RE = re.compile(r'try again in ([\d.]+)\s*s', re.IGNORECASE)


def _resolve_instance(conversation):
    """Instância de envio da conversa: FK direta → vínculo do agente oficial → qualquer conectada.

    Agente override (Conversation.agent != instance.agent) NÃO tem reverse `whatsapp_instance`
    (OneToOne só aponta pro agente oficial). Por isso nunca resolver envio só por
    `agent.whatsapp_instance` — quebra a troca de agente por conversa.
    """
    from integrations.models import WhatsAppInstance
    if conversation.instance_id:
        return conversation.instance
    agent = conversation.agent
    if agent:
        try:
            return agent.whatsapp_instance
        except Exception:
            pass
    return WhatsAppInstance.objects.filter(
        organization_id=conversation.organization_id,
        status=WhatsAppInstance.Status.CONNECTED,
    ).first()

class AgnoInferenceError(Exception):
    '''agent.run() retornou status de erro (Agno engole a excção)'''
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


@shared_task(bind=True, soft_time_limit=90, time_limit=120, max_retries=3)
def transcribe_and_process_message(self, attachment_id: int):
    from conversations.models import MessageAttachment, Message
    from conversations.transcription import transcribe_audio

    try: 
        attachment = MessageAttachment.objects.select_related(
        'message__conversation__agent__provider',
        'message__conversation__instance',
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

    history = conversation.ai_history()

    if history:
        history[-1]['content'] = f'[Audio]: {transcription}'

    try:
        response_text, goal_completed = _call_agno(conversation.agent, history, conversation=conversation, contact=conversation.contact)
    except AgnoInferenceError as e:
        delay = min(e.retry_after or 30 * (2 ** self.request.retries), 120)
        try:
            raise self.retry(exc=e, countdown=delay)
        except self.MaxRetriesExceededError:
            logger.error(f'[transcribe_and_process_message] rate limit persistente, desistindo: {e}')
            return
    except Exception as e:
        logger.error(f'[transcribe_and_process_message] Erro no agno: {e}')
        return

    if goal_completed:
        from conversations.consumers import notify_conversation_updated
        conversation.refresh_from_db()
        notify_conversation_updated(conversation)
        return
    
    if not response_text:
        logger.warning('[transcribe_and_process_message] Agno retornou texto vazio')
        return
    
    agent = conversation.agent

    instance = _resolve_instance(conversation)
    if instance is None:
        logger.error(f'[transcribe_and_process_message] conversa {conversation.id} sem instância de envio')
        return

    if agent.split_messages_enabled:
        from conversations.utils.splitter import split_response
        chunks = split_response(response_text)
    else:
        chunks = [response_text]

    from conversations.consumers import notify_new_message
    if len(chunks) <= 1:
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=response_text,
            agent_name_snapshot=conversation.agent.name if conversation.agent else None,
        )
        notify_new_message(conversation.id, message)
        send_message(
            instance_api_key=instance.instance_api_key,
            phone=conversation.contact.phone,
            text=response_text
        )
    else:
        deliver_split_messages.delay(
            conversation_id=conversation.id,
            instance_id=instance.id,
            chunks=chunks
        )


@shared_task(bind=True, max_retries=3, soft_time_limit=45, time_limit=60)
def send_whatsapp_message(self, message_id: int, instance_id: int = None):
    from conversations.models import Message
    from integrations.models import WhatsAppInstance

    try:
        message = Message.objects.select_related(
            'conversation__contact',
            'conversation__instance',
            'conversation__agent__whatsapp_instance',
            'conversation__organization',
        ).get(id=message_id)

        conv = message.conversation

        if instance_id:
            instance = WhatsAppInstance.objects.filter(id=instance_id, organization=conv.organization).first()
        elif conv.instance_id:
            instance = conv.instance
        elif conv.agent_id and conv.agent:
            instance = conv.agent.whatsapp_instance
        else:
            instance = WhatsAppInstance.objects.filter(
                organization=conv.organization, status=WhatsAppInstance.Status.CONNECTED
            ).first()

        if not instance:
            logger.warning('[send_whatsapp_message] instance not found for message %s', message_id)
            return

        if instance.needs_qr:
            # Sessão desautenticada (LoggedIn=false): /connect não resolve, exige
            # re-scan do QR. Não adianta retentar — aborta sem erro.
            logger.warning('[send_whatsapp_message] instance %s needs QR — envio de %s abortado', instance.id, message_id)
            return

        send_message(
            instance_api_key=instance.instance_api_key,
            phone=conv.contact.phone,
            text=message.content,
        )

    except Exception as exc:
        logger.error('[send_whatsapp_message] failed for message %s: %s', message_id, exc)
        # Falha de envio normalmente = sessão caída -> reconcilia/reconecta a instância
        # (detecção event-driven, sem polling). reconnect_instance decide reconnect vs needs_qr.
        _inst = locals().get('instance')
        if _inst is not None:
            try:
                from integrations.tasks import reconnect_instance
                reconnect_instance.delay(_inst.id)
            except Exception:
                pass
        raise self.retry(exc=exc, countdown=10)

@shared_task
def process_accumulated_messages(conversation_id: int, token: str):
    from conversations.models import Message
    
    key = ACCUMULATE_MARKER_KEY.format(conv_id=conversation_id)
    current = cache.get(key)
    if current != token:
        return
    cache.delete(key)

    last_user_msg = (
        Message.objects.filter(conversation_id=conversation_id, role=Message.Role.USER).order_by('-created_at').first()
    )
    if not last_user_msg:
        return
    process_message.delay(last_user_msg.id)


def schedule_ai_processing(message):
    """Decide entre fire imediato ou debounce baseado no agente."""

    conversation = message.conversation
    agent = conversation.agent
    if not agent or not agent.accumulate_messages_enabled:
        process_message.delay(message.id)
        return
    
    window = max(2, min(60, agent.accumulate_window_seconds))
    token = uuid.uuid4().hex
    cache.set(ACCUMULATE_MARKER_KEY.format(conv_id=conversation.id), token, timeout=window + 30)
    process_accumulated_messages.apply_async(
        args=[conversation.id, token],
        countdown=window
    )

@shared_task(soft_time_limit=30, time_limit=60)
def send_scheduled_message(message_id: int):
    from conversations.models import Message
    from integrations.services import send_message

    try:
        message = Message.objects.select_related(
            'conversation__agent__whatsapp_instance', 'conversation__instance', 'conversation__contact'
        ).get(id=message_id)

        instance = _resolve_instance(message.conversation)
        if not instance:
            logger.error(f'[send_scheduled_message] conversa {message.conversation_id} sem instância de envio')
            Message.objects.filter(id=message_id).update(scheduled_status='failed')
            return
        phone = message.conversation.contact.phone

        send_message(instance_api_key=instance.instance_api_key, phone=phone, text=message.content)

        message.scheduled_status = 'sent'
        message.save(update_fields=['scheduled_status'])

        notify_new_message(message.conversation_id, message)
    
    except Exception as e:
        logger.error(f'[send_scheduled_message] Falha ao enviar mensagem {message_id}: {e}')
        Message.objects.filter(id=message_id).update(scheduled_status='failed')

@shared_task(bind=True, soft_time_limit=90, time_limit=120, max_retries=3)
def process_message(self, message_id: int):
    from conversations.models import Message, Conversation
    from agents.models import AIAgent

    try:
        message = Message.objects.select_related('conversation__agent__provider', 'conversation__instance').get(id=message_id)
    except Message.DoesNotExist:
        return
    
    conversation = message.conversation

    if not conversation.agent:
        return

    if not conversation.ai_active:
        return

    history = conversation.ai_history()

    attachments = list(message.attachments.all())

    from django.utils import timezone
    from datetime import timedelta

    Conversation.objects.filter(id=conversation.id).update(
        follow_up_count=0,
        next_follow_up_at=None
    )
    conversation.refresh_from_db(fields=['follow_up_count', 'next_follow_up_at'])

    try:
        response_text, goal_completed = _call_agno(conversation.agent, history, attachments=attachments, conversation=conversation, contact=conversation.contact)
    except AgnoInferenceError as e:
        delay = min(e.retry_after or 30 * (2 ** self.request.retries), 120)
        try:
            raise self.retry(exc=e, countdown=delay)
        except self.MaxRetriesExceededError:
            logger.error(f'[process_message] rate limit persistente, desistindo: {e}')
            return
    except Exception as e:
        logger.error(f'[process_message] Erro no agno: {e}')
        return
    
    if goal_completed:
        from conversations.consumers import notify_conversation_updated
        conversation.refresh_from_db()
        notify_conversation_updated(conversation)
        return 200

    if not response_text:
        logger.warning('[process_message] Agno retornou response text vazio')
        return

    agent = conversation.agent
    instance = _resolve_instance(conversation)
    if instance is None:
        logger.error(f'[process_message] conversa {conversation.id} sem instância de envio')
        return

    if agent.split_messages_enabled:
        from conversations.utils.splitter import split_response, compute_delay_ms
        chunks = split_response(response_text)
    else:
        chunks = [response_text]

    if len(chunks) <= 1:
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=response_text,
            agent_name_snapshot=conversation.agent.name if conversation.agent else None,
        )
        notify_new_message(conversation.id, assistant_message)
        send_message(instance_api_key=instance.instance_api_key, phone=conversation.contact.phone, text=response_text)  
    else:
        deliver_split_messages.delay(
            conversation_id=conversation.id,
            instance_id=instance.id,
            chunks=chunks
        )

    if conversation.agent and conversation.agent.follow_up_enabled:
        Conversation.objects.filter(id=conversation.id).update(
            next_follow_up_at=timezone.now() + timedelta(minutes=conversation.agent.follow_up_delay)
        )

    return 200

@shared_task
def deliver_split_messages(conversation_id, instance_id, chunks):
    import time
    from conversations.models import Message, Conversation
    from integrations.models import WhatsAppInstance
    from integrations.services import send_message
    from conversations.utils.splitter import compute_delay_ms

    conv = Conversation.objects.select_related('agent', 'contact').get(id=conversation_id)
    instance = WhatsAppInstance.objects.get(id=instance_id)
    agent = conv.agent
    phone = conv.contact.phone

    for i, chunk in enumerate(chunks):
        delay = compute_delay_ms(chunk, agent.split_typing_speed_ms_per_char, agent.split_min_delay_ms, agent.split_max_delay_ms)
        time.sleep(delay / 1000)

        msg = Message.objects.create(
            conversation=conv,
            role=Message.Role.ASSISTANT,
            content=chunk,
            agent_name_snapshot=agent.name if agent else None,
        )
        notify_new_message(conv.id, msg)
        send_message(instance_api_key=instance.instance_api_key, phone=phone, text=chunk)

def _call_agno(agent_config, history, attachments=None, conversation=None, contact=None):
    from agno.agent import Agent
    from agno.models.message import Message as AgnoMessage
    from agno.media import Image
    from agents.models import DocumentChunk
    from agents.embeddings import embed_query
    from pgvector.django import CosineDistance

    model = _get_agno_model(agent_config)
    provider_type = agent_config.provider.provider_type

    rag_context = ''
    last_user = next((m['content'] for m in reversed(history) if m['role'] == 'user'), None)
    if last_user:
        try:
            qvec = embed_query(last_user)
            top = list(
                DocumentChunk.objects.filter(agent=agent_config)
                .order_by(CosineDistance('embedding', qvec))[:6]
            )
            if top:
                joined = '\n\n---\n\n'.join(c.content for c in top)
                rag_context = f'\n\n## Base de conhecimento\n{joined}'
        except Exception as e:
            logger.error(f'[_call_agno] retrieval falhou, seguindo sem RAG: {e}')

    goal_context = ''
    goal_state = {'fired': False}
    if agent_config.goal_enabled and agent_config.goal_description:
        slots = agent_config.goal_slots or []
        required_keys = [s['key'] for s in slots if s.get('required')]
        slots_lines = '\n'.join(
            f'- {s.get("key")}: {s.get("label", "")}' + (' (obrigatório)' if s.get('required') else '')
            for s in slots
        )
        goal_context = (
            f'\n\n## OBJETIVO DESTA CONVERSA\n{agent_config.goal_description}'
            + (f'\n\n### Dados a coletar\n{slots_lines}' if slots_lines else '')
            + (f'\n\n### Critério\nObjetivo cumprido quando os slots obrigatórios estiverem preenchidos: {required_keys} ' if required_keys else '')
            + '\n\nQuando o objetivo estiver cumprido, chame OBRIGATORIAMENTE a ferramenta '
              '`mark_goal_completed(reason, collected)` com justificativa curta e dict dos dados coletados. '
              'IMPORTANTE: ao chamar essa ferramenta, NÃO produza texto de resposta - apenas a chamada. '
              'A mensagem final ao usuário (se configurada) é enviada automaticamente pelo sistema.'
        )

    system = agent_config.system_prompt + rag_context + goal_context

    from agents.tool_factory import get_tools_for_agent
    tools = get_tools_for_agent(agent_config, conversation=conversation, contact=contact, goal_state=goal_state)

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
    
    from agno.run.base import RunStatus
    if getattr(response, 'status', None) == RunStatus.error:
        content = response.content or 'erro de inferência desconhecido'
        m = _RETRY_RE.search(str(content))
        raise AgnoInferenceError(content, retry_after=float(m.group(1)) if m else None)
    
    if goal_state.get('fired'):
        logger.info(f'[_call_agno] goal completed conv={conversation.id} reason={goal_state.get("reason")!r}')
    return response.content, goal_state.get('fired', False)

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

@shared_task(bind=True, soft_time_limit=90, time_limit=120, max_retries=3)
def send_follow_up(self, conversation_id: int):
    from django.utils import timezone
    from conversations.models import Conversation, Message

    try:
        conv = Conversation.objects.select_related(
            'agent__provider', 'agent__whatsapp_instance', 'instance', 'contact'
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
    
    history = conv.ai_history()

    extra = conv.agent.follow_up_prompt or 'O usuário não respondeu. Envie uma mensagem de follow-up para retomar a conversa.'
    original_prompt = conv.agent.system_prompt
    conv.agent.system_prompt = f'{original_prompt}\n\n[FOLLOW-UP {conv.follow_up_count + 1}/{conv.agent.max_follow_ups}]: {extra}'

    try:
        response_text, goal_completed = _call_agno(conv.agent, history, conversation=conv, contact=conv.contact)
    except AgnoInferenceError as e:
        delay = min(e.retry_after or 30 * (2 ** self.request.retries), 120)
        try:
            raise self.retry(exc=e, countdown=delay)
        except self.MaxRetriesExceededError:
            logger.error(f'[send_follow_up] rate limit persistente, desistindo: {e}')
            return
    except Exception as e:
        logger.error(f'[send_follow_up] Erro no agno {e}')
        return
    finally:
        conv.agent.system_prompt = original_prompt

    if goal_completed:
        conv.refresh_from_db()
        notify_conversation_updated(conv)
        return

    if not response_text:
        return
    

    message = Message.objects.create(
        conversation=conv,
        role=Message.Role.ASSISTANT,
        content=response_text,
        agent_name_snapshot=conv.agent.name if conv.agent else None,
    )

    notify_new_message(conv.id, message)

    instance = _resolve_instance(conv)
    if instance is None:
        logger.error(f'[send_follow_up] conversa {conv.id} sem instância de envio')
        return
    try:
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
