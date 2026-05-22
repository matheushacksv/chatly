from django.db import models
from accounts.models import Organization


TRIGGER_CHOICES = [
    ('contact.created', 'Contato criado'),
    ('conversation.created', 'Conversa criada'),
    ('conversation.closed', 'Conversa fechada'),
    ('message.received', 'Mensagem recebida'),
    ('agent.goal_completed', 'Objetivo do agente cumprido'),
    ('automation.chained', 'Iniciada por automação'),
]

ACTION_CHOICES = [
    ('send_message', 'Enviar mensagem'),
    ('send_template', 'Enviar template'),
    ('http_request', 'Requisição HTTP'),
    ('toggle_ai', 'Ativar/desativar IA'),
    ('switch_agent', 'Trocar agente de IA'),
    ('add_label', 'Adicionar etiqueta'),
    ('condition', 'Condição (Se/Senão)'),
    ('remove_label', 'Remover etiqueta'),
    ('start_automation', 'Iniciar outra automação'),
    ('wait_delay', 'Aguardar'),
    ('assign_to_user', 'Atribuir a usuário'),
    ('close_conversation', 'Fechar conversa'),
    ('update_deal_stage', 'Mudar etapa do deal (Pipedrive)'),
]


class Automation(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='automations')
    name = models.CharField(max_length=120)
    trigger_type = models.CharField(max_length=64, choices=TRIGGER_CHOICES, db_index=True)
    trigger_filters = models.JSONField(default=dict, blank=True)
    variant_state = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['organization', 'trigger_type', 'is_active'])]
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class AutomationStep(models.Model):
    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, related_name='steps')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    branch = models.CharField(max_length=8, default='', blank=True)
    order = models.PositiveIntegerField()
    action_type = models.CharField(max_length=64, choices=ACTION_CHOICES)
    config = models.JSONField(default=dict)

    class Meta:
        ordering = ['order']
        unique_together = ('automation', 'order')


class AutomationRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    automation = models.ForeignKey(Automation, on_delete=models.CASCADE, related_name='runs')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    context = models.JSONField(default=dict)
    current_step = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
