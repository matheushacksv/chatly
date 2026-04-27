from ninja import Schema, ModelSchema
from typing import Optional
from templates.models import MessageTemplate


class MessageTemplateOut(ModelSchema):
    class Meta:
        model = MessageTemplate
        fields = ['id', 'title', 'shortcut', 'media_type', 'content',
        'file_url', 'mime_type', 'created_at']

class MessageTemplateIn(Schema):
    title: str
    shortcut: str = ''
    content: str = ''
