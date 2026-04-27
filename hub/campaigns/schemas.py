from datetime import datetime
from typing import Optional
from ninja import Schema

class CampaignMessageIn(Schema):
    content: str

class CampaignMessageOut(Schema):
    id: int
    content: str
    order: int

class CampaignIn(Schema):
    name: str
    instance_id: int
    agent_id: Optional[int] = None
    ai_active: bool = False
    interval_min: int = 5
    interval_max: int = 15
    messages: list[CampaignMessageIn]

class CampaignPatchIn(Schema):
    name: Optional[str] = None
    instance_id: Optional[int] = None
    agent_id: Optional[int] = None
    ai_active: Optional[bool] = None
    interval_min: Optional[int] = None
    interval_max: Optional[int] = None
    messages: Optional[list[CampaignMessageIn]] = None

class AddContactsIn(Schema):
    contact_ids: list[int] = []
    label_ids: list[int] = []
    add_all: bool = False

class CampaignOut(Schema):
    id: int
    name: str
    status: str
    total_contacts: int
    sent_count: int
    failed_count: int
    interval_min: int
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime
    instance_id: int
    agent_id: Optional[int]
    ai_active: bool
    messages: list[CampaignMessageOut] = []

    @staticmethod
    def resolve_messages(obj):
        return obj.messages.order_by('order')

class CampaignContactOut(Schema):
    id: int
    contact_id: int
    contact_name: str
    contact_phone: str
    status: str
    sent_at: Optional[datetime]
    error: Optional[str]

    @staticmethod
    def resolve_contact_name(obj):
        return obj.contact.name

    @staticmethod
    def resolve_contact_phone(obj):
        return obj.contact.phone

