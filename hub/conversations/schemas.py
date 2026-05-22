from ninja import Schema, ModelSchema
from typing import Optional
from datetime import datetime
from conversations.models import Conversation, Message
from labels.schemas import LabelOut


class AttachmentOut(Schema):
    id: int
    media_type: str
    file_url: str
    mime_type: str
    transcription: str = ''
    transcription_status: str

class MessageOut(ModelSchema):
    attachments: list[AttachmentOut] = []
    sent_by_name: Optional[str] = None

    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'created_at', 'scheduled_at', 'scheduled_status']

    @staticmethod
    def resolve_sent_by_name(obj):
        return obj.sent_by.name if obj.sent_by_id and obj.sent_by else None

class ContactOut(Schema):
    id: int
    name: str
    phone: str
    labels: list[LabelOut] = []

class LastMessageOut(Schema):
    id: int
    role: str
    content: str
    created_at: datetime


class ConversationOut(ModelSchema):
    contact: ContactOut
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None
    last_message: Optional[LastMessageOut] = None
    labels: list[LabelOut] = []
    instance_id: Optional[int] = None
    instance_name: Optional[str] = None
    pipedrive_deal_id: Optional[int] = None

    follow_up_count: int = 0
    next_follow_up_at: Optional[datetime] = None

    class Meta:
        model = Conversation
        fields = ['id', 'status', 'ai_active', 'started_at', 'ended_at']

    @staticmethod
    def resolve_follow_up_count(obj):
        return obj.follow_up_count or 0

    @staticmethod
    def resolve_next_follow_up_at(obj):
        return obj.next_follow_up_at

    @staticmethod
    def resolve_agent_id(obj):
        return obj.agent_id

    @staticmethod
    def resolve_agent_name(obj):
        return obj.agent.name if obj.agent_id and obj.agent else None

    @staticmethod
    def resolve_assigned_to_id(obj):
        return obj.assigned_to_id

    @staticmethod
    def resolve_assigned_to_name(obj):
        return obj.assigned_to.name if obj.assigned_to_id and obj.assigned_to else None

    @staticmethod
    def resolve_labels(obj):
        return obj.labels.all()

    @staticmethod
    def resolve_instance_id(obj):
        return obj.instance_id

    @staticmethod
    def resolve_instance_name(obj):
        return obj.instance.phone_number if obj.instance_id and obj.instance else None

    @staticmethod
    def resolve_last_message(obj):
        if hasattr(obj, '_last_msg_id') and obj._last_msg_id is not None:
            return {
                'id': obj._last_msg_id,
                'role': obj._last_msg_role,
                'content': obj._last_msg_content or '',
                'created_at': obj._last_msg_created_at,
            }
        msg = obj.messages.order_by('-created_at').first()
        if not msg:
            return None
        return {'id': msg.id, 'role': msg.role, 'content': msg.content or '', 'created_at': msg.created_at}

class UpdateConversationIn(Schema):
    status: Optional[str] = None
    ai_active: Optional[bool] = None
    assigned_to_id: Optional[int] = None
    agent_id: Optional[int] = None

class SendMessageIn(Schema):
    content: str
    scheduled_at: Optional[datetime] = None

class StickerOut(Schema):
    id: int
    name: str
    file_url: str
    created_at: datetime

class SendStickerIn(Schema):
    sticker_id: int

class StartConversationIn(Schema):
    phone: str
    name: str = ''
    email: str = ''
    instance_id: int
    agent_id: Optional[int] = None
    message: str = ''
    pipedrive_person_id: Optional[int] = None
