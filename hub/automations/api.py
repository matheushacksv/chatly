from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router

from core.utils.errors import GenericErrorSchema

from .models import Automation, AutomationStep, AutomationRun, TRIGGER_CHOICES, ACTION_CHOICES
from .schemas import (
    AutomationIn, AutomationOut, AutomationListOut, AutomationRunOut,
    ToggleIn, TriggerMeta, ActionMeta,
)

router = Router(tags=['Automations'])


TRIGGERS_META = [{'type': t, 'label': l} for t, l in TRIGGER_CHOICES]

ACTIONS_META = [
    {
        'type': 'send_message',
        'label': 'Enviar mensagem',
        'fields': [
            {'key': 'instance_id', 'label': 'Instância', 'type': 'instance_select', 'required': True},
            {'key': 'text', 'label': 'Texto', 'type': 'textarea', 'required': True},
        ],
    },
    {
        'type': 'send_template',
        'label': 'Enviar template',
        'fields': [
            {'key': 'instance_id', 'label': 'Instância', 'type': 'instance_select', 'required': True},
            {'key': 'template_id', 'label': 'Template', 'type': 'template_select', 'required': True},
        ],
    },
    {
        'type': 'http_request',
        'label': 'Requisição HTTP',
        'fields': [
            {'key': 'method', 'label': 'Método', 'type': 'select', 'required': True,
             'options': [{'value': 'GET', 'label': 'GET'}, {'value': 'POST', 'label': 'POST'},
                         {'value': 'PUT', 'label': 'PUT'}, {'value': 'PATCH', 'label': 'PATCH'},
                         {'value': 'DELETE', 'label': 'DELETE'}]},
            {'key': 'url', 'label': 'URL', 'type': 'text', 'required': True},
            {'key': 'headers', 'label': 'Headers (JSON)', 'type': 'json'},
            {'key': 'body', 'label': 'Body', 'type': 'textarea'},
        ],
    },
    {
        'type': 'toggle_ai',
        'label': 'Ativar/desativar IA',
        'fields': [
            {'key': 'value', 'label': 'Ativar IA', 'type': 'boolean', 'required': True},
        ],
    },
    {
        'type': 'add_label',
        'label': 'Adicionar etiqueta',
        'fields': [
            {'key': 'label_id', 'label': 'Etiqueta', 'type': 'label_select', 'required': True},
            {'key': 'target', 'label': 'Aplicar em', 'type': 'select', 'required': True,
             'options': [{'value': 'conversation', 'label': 'Conversa'}, {'value': 'contact', 'label': 'Contato'}]},
        ],
    },
    {
        'type': 'remove_label',
        'label': 'Remover etiqueta',
        'fields': [
            {'key': 'label_id', 'label': 'Etiqueta', 'type': 'label_select', 'required': True},
            {'key': 'target', 'label': 'Remover de', 'type': 'select', 'required': True,
             'options': [{'value': 'conversation', 'label': 'Conversa'}, {'value': 'contact', 'label': 'Contato'}]},
        ],
    },
    {
        'type': 'wait_delay',
        'label': 'Aguardar',
        'fields': [
            {'key': 'seconds', 'label': 'Segundos', 'type': 'number', 'required': True},
        ],
    },
    {
        'type': 'assign_to_user',
        'label': 'Atribuir a usuário',
        'fields': [
            {'key': 'user_id', 'label': 'Usuário', 'type': 'user_select', 'required': True},
        ],
    },
    {
        'type': 'close_conversation',
        'label': 'Fechar conversa',
        'fields': [],
    },
]


@router.get('/triggers/', response=list[TriggerMeta])
def list_triggers(request):
    return TRIGGERS_META


@router.get('/actions/', response=list[ActionMeta])
def list_actions(request):
    return ACTIONS_META


@router.get('/', response=list[AutomationListOut])
def list_automations(request):
    return list(
        Automation.objects.filter(organization=request.auth.organization).prefetch_related('steps')
    )


@router.post('/', response={201: AutomationOut, 400: GenericErrorSchema})
def create_automation(request, data: AutomationIn):
    valid_triggers = {t for t, _ in TRIGGER_CHOICES}
    if data.trigger_type not in valid_triggers:
        return 400, {'detail': f'trigger_type inválido: {data.trigger_type}'}

    valid_actions = {a for a, _ in ACTION_CHOICES}
    for step in data.steps:
        if step.action_type not in valid_actions:
            return 400, {'detail': f'action_type inválido: {step.action_type}'}

    with transaction.atomic():
        automation = Automation.objects.create(
            organization=request.auth.organization,
            name=data.name,
            trigger_type=data.trigger_type,
            trigger_filters=data.trigger_filters,
            is_active=data.is_active,
        )
        AutomationStep.objects.bulk_create([
            AutomationStep(
                automation=automation,
                order=s.order,
                action_type=s.action_type,
                config=s.config,
            ) for s in data.steps
        ])

    return 201, automation


@router.get('/{automation_id}/', response={200: AutomationOut, 404: GenericErrorSchema})
def get_automation(request, automation_id: int):
    automation = get_object_or_404(
        Automation.objects.prefetch_related('steps'),
        id=automation_id, organization=request.auth.organization,
    )
    return automation


@router.patch('/{automation_id}/', response={200: AutomationOut, 400: GenericErrorSchema})
def update_automation(request, automation_id: int, data: AutomationIn):
    automation = get_object_or_404(Automation, id=automation_id, organization=request.auth.organization)

    valid_triggers = {t for t, _ in TRIGGER_CHOICES}
    if data.trigger_type not in valid_triggers:
        return 400, {'detail': f'trigger_type inválido: {data.trigger_type}'}

    valid_actions = {a for a, _ in ACTION_CHOICES}
    for step in data.steps:
        if step.action_type not in valid_actions:
            return 400, {'detail': f'action_type inválido: {step.action_type}'}

    with transaction.atomic():
        automation.name = data.name
        automation.trigger_type = data.trigger_type
        automation.trigger_filters = data.trigger_filters
        automation.is_active = data.is_active
        automation.save()

        automation.steps.all().delete()
        AutomationStep.objects.bulk_create([
            AutomationStep(
                automation=automation,
                order=s.order,
                action_type=s.action_type,
                config=s.config,
            ) for s in data.steps
        ])

    return automation


@router.delete('/{automation_id}/', response={204: None})
def delete_automation(request, automation_id: int):
    automation = get_object_or_404(Automation, id=automation_id, organization=request.auth.organization)
    automation.delete()
    return 204, None


@router.post('/{automation_id}/toggle/', response={200: AutomationOut})
def toggle_automation(request, automation_id: int, data: ToggleIn):
    automation = get_object_or_404(Automation, id=automation_id, organization=request.auth.organization)
    automation.is_active = data.is_active
    automation.save(update_fields=['is_active', 'updated_at'])
    return automation


@router.get('/{automation_id}/runs/', response=list[AutomationRunOut])
def list_runs(request, automation_id: int, limit: int = 50):
    automation = get_object_or_404(Automation, id=automation_id, organization=request.auth.organization)
    return list(automation.runs.order_by('-started_at')[:limit])
