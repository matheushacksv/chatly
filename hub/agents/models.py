from django.db import models
from accounts.models import Organization
from encrypted_model_fields.fields import EncryptedTextField

class AIProvider(models.Model):
    class ProviderType(models.TextChoices):
        OPENAI = 'openai', 'OpenAI'
        ANTHROPIC = 'anthropic', 'Anthropic'
        GROQ = 'groq', 'Groq'

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='providers')
    provider_type = models.CharField(max_length=20, choices=ProviderType.choices)
    api_key = EncryptedTextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'provider_type')

    def __str__(self):
        return f'{self.organization} - {self.provider_type}'


class AIAgent(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='agents')
    provider = models.ForeignKey(AIProvider, on_delete=models.PROTECT, related_name='agents')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    system_prompt = models.TextField()
    model_name = models.CharField(max_length=100)
    enabled_tools = models.JSONField(default=list, blank=True)
    memory_enabled = models.BooleanField(default=False)
    memory_type = models.CharField(max_length=20, choices=[('per_contact', 'Por contato'), ('global', 'Global')], default='per_contact')
    is_active = models.BooleanField(default=True)
    follow_up_enabled = models.BooleanField(default=False)
    follow_up_delay = models.PositiveIntegerField(default=60)
    max_follow_ups = models.PositiveIntegerField(default=3)
    follow_up_prompt = models.TextField(blank=True, default='')
    follow_up_respect_hours = models.BooleanField(default=False)
    goal_enabled = models.BooleanField(default=False)
    goal_description = models.TextField(blank=True, default='')
    goal_slots = models.JSONField(default=list, blank=True)

    GOAL_ACTION_CHOICES = [
        ('deactivate_ai', 'Desativar IA'),
        ('close_conversation', 'Fechar conversa'),
        ('assign_to_user', 'Atribuir a usuário'),
        ('trigger_automation', 'Disparar automação')
    ]
    goal_action = models.CharField(choices=GOAL_ACTION_CHOICES, blank=True, default='')
    goal_assign_to = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='goal_assignments')
    goal_final_message = models.TextField(blank=True, default='')

    split_messages_enabled = models.BooleanField(default=False)
    split_typing_speed_ms_per_char = models.PositiveIntegerField(default=35)
    split_min_delay_ms = models.PositiveIntegerField(default=600)
    split_max_delay_ms = models.PositiveIntegerField(default=3500)

    accumulate_messages_enabled = models.BooleanField(default=False)
    accumulate_window_seconds = models.PositiveIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class AgentDocument(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        PROCESSING = 'processing', 'Processando'
        READY = 'ready', 'Pronto'
        FAILED = 'failed', 'Falhou'

    agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='documents')
    name = models.CharField(max_length=255)
    file_url = models.URLField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class AgentCustomTool(models.Model):
    METHOD_CHOICES = [('GET', 'GET'),('POST', 'POST'),('PUT', 'PUT'),('PATCH', 'PATCH'),('DELETE', 'DELETE')]

    agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='custom_tools')
    name = models.SlugField(max_length=100)
    description = models.TextField()
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    url = models.CharField(max_length=2048)
    headers = EncryptedTextField(blank=True, default='{}')
    body_template = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('agent', 'name')]
        ordering = ['-created_at']

class AgentMembership(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='agent_memberships')
    agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='memberships')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'agent')

    def __str__(self):
        return f'{self.user} → {self.agent}'

class GoalCompletion(models.Model):
    agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='completions')
    conversation = models.ForeignKey('conversations.Conversation', on_delete=models.CASCADE, related_name='goal_completions')
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)
    collected_data = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['agent', '-created_at'])]
