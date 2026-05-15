from django.db import models
from accounts.models import Organization
from agents.models import AIAgent
from contacts.models import Contact
from django.conf import settings
from labels.models import Label

class Conversation(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        CLOSED = 'closed', 'Closed'
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='conversations')
    agent = models.ForeignKey(AIAgent, on_delete=models.SET_NULL, null=True, related_name='conversations')
    ai_active = models.BooleanField(default=False)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='conversations')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_conversations')
    labels = models.ManyToManyField(Label, blank=True, related_name='conversations')
    instance = models.ForeignKey('integrations.WhatsAppInstance', null=True, blank=True, on_delete=models.SET_NULL, related_name='conversations')
    pipedrive_deal_id = models.IntegerField(null=True, blank=True)
    follow_up_count = models.PositiveIntegerField(default=0)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL, null=True, blank=True)
    memory_reset_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', '-started_at'])
        ]

    def ai_history(self, limit=50):
        qs = self.messages.all()
        if self.memory_reset_at:
            qs = qs.filter(created_at__gt=self.memory_reset_at)
        history = list(qs.order_by('-created_at').values('role', 'content')[:limit])
        history.reverse()
        return history

    def __str__(self):
        return f'{self.contact}'

class Message(models.Model):

    class ScheduledStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'
        SYSTEM = 'system', 'System'
        OPERATOR = 'operator', 'Operator'

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_messages')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    scheduled_status = models.CharField(max_length=10, choices=ScheduledStatus.choices, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['conversation', 'created_at'])
        ]

    def __str__(self):
        return f'{self.role}: {self.content[:50]}'

class MessageAttachment(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = 'image', 'Image'
        AUDIO = 'audio', 'Audio'
        DOCUMENT = 'document', 'Document'
        VIDEO = 'video', 'Video'
        GIF = 'gif', 'GIF'
        STICKER = 'sticker', 'Sticker'

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    file_url = models.URLField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    transcription = models.TextField(blank=True)
    transcription_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)


class Sticker(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='stickers')
    name = models.CharField(max_length=100, blank=True)
    file_url = models.URLField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='saved_stickers')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f'Sticker {self.id}'
