import uuid
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from accounts.models import Organization
from agents.models import AIAgent
from encrypted_model_fields.fields import EncryptedTextField

class WhatsAppInstance(models.Model):
    class Status(models.TextChoices):
        CONNECTED = 'connected', 'Connected'
        DISCONNECTED = 'disconnected', 'Disconnected'
        CONNECTING = 'connecting', 'Connecting'

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='whatsapp_instances')
    agent = models.OneToOneField(AIAgent, on_delete=models.SET_NULL, null=True, blank=True, related_name='whatsapp_instance')
    instance_name = models.CharField(max_length=255, unique=True)
    instance_api_key = models.TextField()
    phone_number = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DISCONNECTED)
    created_at = models.DateTimeField(auto_now_add=True)

class PipedriveIntegration(models.Model):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='pipedrive_integration')
    api_key = EncryptedTextField()
    is_active = models.BooleanField(default=True)
    webhook_secret = models.UUIDField(default=uuid.uuid4, unique=True)

    sync_contacts = models.BooleanField(default=False)
    auto_create_deal = models.BooleanField(default=False)
    auto_close_deal = models.BooleanField(default=False)
    deal_pipeline_id = models.IntegerField(null=True, blank=True)
    deal_stage_id = models.IntegerField(null=True, blank=True)
    extra_config = models.JSONField(default=dict, blank=True)
    #last_sync_at
    #webhook_id

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'PipedriveIntegration({self.organization.slug})'

class AssignmentQueue(models.Model):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    channel_instance = GenericForeignKey('content_type', 'object_id')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('content_type', 'object_id')

class AssignmentQueueMember(models.Model):
    queue = models.ForeignKey(AssignmentQueue, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    percentage = models.IntegerField()
    assignment_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ('queue', 'user')



