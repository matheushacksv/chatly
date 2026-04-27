from accounts.models import User
from django.db import models
from accounts.models import Organization
from integrations.models import WhatsAppInstance
from agents.models import AIAgent
from contacts.models import Contact

class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        RUNNING = 'running', 'Enviando'
        PAUSED = 'paused', 'Pausada'
        FINISHED = 'finished', 'Concluída'
        CANCELLED = 'cancelled', 'Cancelada'

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    instance = models.ForeignKey(WhatsAppInstance, on_delete=models.CASCADE)
    agent = models.ForeignKey(AIAgent, null=True, on_delete=models.SET_NULL)
    ai_active = models.BooleanField(default=False)
    status = models.CharField(choices=Status.choices, default='draft')

    interval_min = models.PositiveIntegerField(default=5)
    interval_max = models.PositiveIntegerField(default=15)

    total_contacts = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)

    finished_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True)
    started_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CampaignMessage(models.Model):
    '''Variantes da mensagem inicial'''

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)

class CampaignContact(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending'
        SENT = 'sent'
        FAILED = 'failed'
        SKIPPED = 'skipped'

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='contacts')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    status = models.CharField(choices=Status.choices, default='pending')
    message_sent = models.TextField(null=True, blank=True)
    conversation = models.ForeignKey('conversations.Conversation', on_delete=models.CASCADE, null=True)
    sent_at = models.DateTimeField(null=True)
    error = models.TextField(null=True)

    class Meta:
        unique_together = ('campaign', 'contact')