from django.db import models
from accounts.models import Organization
from django.conf import settings

class MessageTemplate(models.Model):
    class MediaType(models.TextChoices):
        TEXT = 'text', 'Text'
        DOCUMENT = 'document', 'Document'
        IMAGE = 'image', 'Image'
        AUDIO = 'audio', 'Audio'
        STICKER = 'sticker', 'Sticker'
        
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='message_templates')
    title = models.CharField(max_length=100)
    shortcut = models.CharField(max_length=50, blank=True)
    media_type = models.CharField(max_length=20, choices=MediaType.choices, default=MediaType.TEXT)
    content = models.TextField(blank=True)
    file_url = models.URLField(blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


