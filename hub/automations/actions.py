import logging
import httpx
from django.utils import timezone
from automations.models import Automation, AutomationRun
from automations.tasks import run_automation

from .templating import render_template, build_context

logger = logging.getLogger(__name__)

ACTION_HANDLERS = {}
MAX_AUTO_DEPTH = 5


def register(name):
    def deco(fn):
        ACTION_HANDLERS[name] = fn
        return fn
    return deco


def execute_action(step, run_context: dict, organization_id: int):
    handler = ACTION_HANDLERS.get(step.action_type)
    if handler is None:
        raise ValueError(f'Action handler não encontrado: {step.action_type}')
    handler(step.config, run_context, organization_id)


def _get_conversation(run_context: dict, organization_id: int):
    from conversations.models import Conversation
    conv_id = run_context.get('conversation_id')
    if not conv_id:
        return None
    return Conversation.objects.filter(id=conv_id, organization_id=organization_id).select_related('contact', 'instance', 'agent__whatsapp_instance').first()


def _get_contact(run_context: dict, organization_id: int):
    from contacts.models import Contact
    contact_id = run_context.get('contact_id')
    if not contact_id:
        return None
    return Contact.objects.filter(id=contact_id, organization_id=organization_id).first()


def _resolve_instance(conv):
    if conv is None:
        return None
    if conv.instance_id:
        return conv.instance
    if conv.agent_id and conv.agent:
        return conv.agent.whatsapp_instance
    return None


def _resolve_instance_id(config: dict, conv, organization_id: int):
    from integrations.models import WhatsAppInstance
    instance_id = config.get('instance_id')
    if instance_id:
        exists = WhatsAppInstance.objects.filter(id=instance_id, organization_id=organization_id).exists()
        if not exists:
            raise RuntimeError(f'instância {instance_id} não encontrada na organização')
        return int(instance_id)
    if conv and conv.instance_id:
        return conv.instance_id
    raise ValueError('instance_id é obrigatório (configure na ação ou na conversa)')

@register('start_automation')
def _start_automation(config, run_context, organization_id):
    target_id = config.get('automation_id')
    if not target_id:
        raise ValueError('start_automation: automation_id é obrigatório')
    
    depth = int(run_context.get('_auto_depth', 0))
    if depth >= MAX_AUTO_DEPTH:
        raise ValueError('start_automation: profundidade máxima de encadeamento atingida')
    target = Automation.objects.filter(
        id=target_id, organization_id=organization_id, is_active=True, trigger_type='automation.chained',
    ).first()
    if target is None:
        raise RuntimeError(f'start_automation: automação {target_id} não encontrada/inativa ou sem gatilho "Iniciada por automação"')
    ctx = {k: v for k, v in run_context.items()
           if k in ('conversation_id', 'contact_id', 'agent_id', 'collected')}
    ctx['_auto_depth'] = depth + 1
    new_run = AutomationRun.objects.create(automation=target, context=ctx)
    run_automation.delay(new_run.id)

@register('send_message')
def _send_message(config: dict, run_context: dict, organization_id: int):
    from conversations.models import Message, Conversation
    from conversations.tasks import send_whatsapp_message
    from integrations.models import WhatsAppInstance

    conv = _get_conversation(run_context, organization_id)
    contact = _get_contact(run_context, organization_id) if conv is None else conv.contact

    if conv is None and contact is None:
        raise ValueError('send_message: contexto sem conversation_id nem contact_id — automação mal configurada para esse trigger')

    if conv is None:
        configured_instance_id = config.get('instance_id')
        if configured_instance_id:
            inst = WhatsAppInstance.objects.filter(id=configured_instance_id, organization_id=organization_id).first()
        else:
            inst = WhatsAppInstance.objects.filter(
                organization_id=organization_id,
                status=WhatsAppInstance.Status.CONNECTED,
            ).first()
        if inst is None:
            raise ValueError('send_message: nenhuma instância WhatsApp disponível para abrir conversa')
        conv = Conversation.objects.create(
            organization_id=organization_id,
            contact=contact,
            status=Conversation.Status.OPEN,
            instance=inst,
        )

    instance_id = _resolve_instance_id(config, conv, organization_id)
    if conv.instance_id != instance_id:
        conv.instance_id = instance_id
        conv.save(update_fields=['instance'])

    text = render_template(config.get('text', ''), build_context(run_context))
    if not text:
        raise ValueError('send_message: texto vazio após renderização')

    message = Message.objects.create(
        conversation=conv,
        role=Message.Role.ASSISTANT,
        content=text,
    )
    send_whatsapp_message.delay(message.id, instance_id=instance_id)


@register('send_template')
def _send_template(config: dict, run_context: dict, organization_id: int):
    from conversations.models import Message
    from conversations.tasks import send_whatsapp_message
    from templates.models import MessageTemplate

    template_id = config.get('template_id')
    if not template_id:
        raise ValueError('send_template: template_id é obrigatório')

    template = MessageTemplate.objects.filter(id=template_id, organization_id=organization_id).first()
    if template is None:
        raise RuntimeError(f'send_template: template {template_id} não encontrado')

    conv = _get_conversation(run_context, organization_id)
    if conv is None:
        contact = _get_contact(run_context, organization_id)
        if contact is None:
            raise RuntimeError('send_template: contato/conversa não encontrados')
        from conversations.models import Conversation
        conv = Conversation.objects.create(
            organization_id=organization_id,
            contact=contact,
            status=Conversation.Status.OPEN,
        )

    instance_id = _resolve_instance_id(config, conv, organization_id)
    if conv.instance_id != instance_id:
        conv.instance_id = instance_id
        conv.save(update_fields=['instance'])

    text = render_template(template.content or '', build_context(run_context))
    message = Message.objects.create(
        conversation=conv,
        role=Message.Role.ASSISTANT,
        content=text,
    )
    send_whatsapp_message.delay(message.id, instance_id=instance_id)


@register('http_request')
def _http_request(config: dict, run_context: dict, organization_id: int):
    url = config.get('url', '')
    if not url:
        raise ValueError('http_request: url é obrigatória')

    method = (config.get('method') or 'POST').upper()
    headers = config.get('headers') or {}
    body_template = config.get('body') or ''
    ctx = build_context(run_context)

    rendered_url = render_template(url, ctx)
    rendered_body = render_template(body_template, ctx) if isinstance(body_template, str) else body_template

    kwargs = {'headers': headers, 'timeout': 30.0, 'follow_redirects': True}
    if method in ('POST', 'PUT', 'PATCH'):
        if isinstance(rendered_body, str) and rendered_body.strip().startswith('{'):
            import json
            try:
                kwargs['json'] = json.loads(rendered_body)
            except json.JSONDecodeError:
                kwargs['content'] = rendered_body
        else:
            kwargs['content'] = rendered_body or ''

    response = httpx.request(method, rendered_url, **kwargs)
    response.raise_for_status()


@register('toggle_ai')
def _toggle_ai(config: dict, run_context: dict, organization_id: int):
    from conversations.models import Conversation
    conv = _get_conversation(run_context, organization_id)
    if conv is None:
        raise RuntimeError('toggle_ai: conversation não encontrada no contexto')
    value = bool(config.get('value', True))
    Conversation.objects.filter(id=conv.id).update(ai_active=value)


@register('add_label')
def _add_label(config: dict, run_context: dict, organization_id: int):
    label_id = config.get('label_id')
    target = config.get('target', 'conversation')
    if not label_id:
        raise ValueError('add_label: label_id é obrigatório')

    if target == 'conversation':
        conv = _get_conversation(run_context, organization_id)
        if conv is None:
            raise RuntimeError('add_label: conversation não encontrada')
        conv.labels.add(label_id)
    else:
        contact = _get_contact(run_context, organization_id)
        if contact is None:
            raise RuntimeError('add_label: contact não encontrado')
        contact.labels.add(label_id)


@register('remove_label')
def _remove_label(config: dict, run_context: dict, organization_id: int):
    label_id = config.get('label_id')
    target = config.get('target', 'conversation')
    if not label_id:
        raise ValueError('remove_label: label_id é obrigatório')

    if target == 'conversation':
        conv = _get_conversation(run_context, organization_id)
        if conv is None:
            raise RuntimeError('remove_label: conversation não encontrada')
        conv.labels.remove(label_id)
    else:
        contact = _get_contact(run_context, organization_id)
        if contact is None:
            raise RuntimeError('remove_label: contact não encontrado')
        contact.labels.remove(label_id)


@register('assign_to_user')
def _assign_to_user(config: dict, run_context: dict, organization_id: int):
    from conversations.models import Conversation
    user_id = config.get('user_id')
    if not user_id:
        raise ValueError('assign_to_user: user_id é obrigatório')

    conv = _get_conversation(run_context, organization_id)
    if conv is None:
        raise RuntimeError('assign_to_user: conversation não encontrada')
    Conversation.objects.filter(id=conv.id).update(assigned_to_id=user_id)


@register('close_conversation')
def _close_conversation(config: dict, run_context: dict, organization_id: int):
    from conversations.models import Conversation
    conv = _get_conversation(run_context, organization_id)
    if conv is None:
        raise RuntimeError('close_conversation: conversation não encontrada')
    Conversation.objects.filter(id=conv.id).update(
        status=Conversation.Status.CLOSED,
        ended_at=timezone.now(),
    )


@register('update_deal_stage')
def _update_deal_stage(config: dict, run_context: dict, organization_id: int):
    from conversations.models import Conversation
    from integrations.models import PipedriveIntegration
    from integrations.pipedrive_services import update_deal_stage

    stage_id = config.get('stage_id')
    if not stage_id:
        raise ValueError('update_deal_stage: stage_id é obrigatório')

    integration = PipedriveIntegration.objects.filter(
        organization_id=organization_id, is_active=True,
    ).first()
    if integration is None:
        logger.warning('update_deal_stage: integração Pipedrive inativa — pulando')
        return

    conv = _get_conversation(run_context, organization_id)
    deal_id = conv.pipedrive_deal_id if conv else None

    if not deal_id:
        contact = _get_contact(run_context, organization_id)
        if contact:
            deal_id = (
                Conversation.objects
                .filter(contact=contact, organization_id=organization_id)
                .exclude(pipedrive_deal_id__isnull=True)
                .order_by('-started_at')
                .values_list('pipedrive_deal_id', flat=True)
                .first()
            )

    if not deal_id:
        logger.info('update_deal_stage: nenhum deal para o contato — pulando')
        return

    update_deal_stage(integration.api_key, int(deal_id), int(stage_id))
