from typing import Any
from ninja import Schema
from typing import Optional

#* ----- WhatsApp -----

class WhatsAppInstanceIn(Schema):
    name: str
    agent_id: Optional[int] = None

class WhatsAppInstanceOut(Schema):
    id: int
    instance_name: str
    phone_number: str
    status: str
    agent_id: Optional[int] = None

    @staticmethod
    def resolve_agent_id(obj):
        return obj.agent_id

class ConnectIn(Schema):
    phone: Optional[str] = None


class QRCodeOut(Schema):
    qrcode: str
    code: str

    @staticmethod
    def resolve_qrcode(obj):
        return obj.get('Qrcode', '')

    @staticmethod
    def resolve_code(obj):
        return obj.get('Code', '')

class PairCodeIn(Schema):
    phone: str

class PairCodeOut(Schema):
    paircode: str

class WebhookPayload(Schema):
    event: str = ''
    data: Any = None
    instanceName: str = ''
    instanceId: str = ''
    instanceToken: str = ''
    state: str = ''


#* ----- Pipedrive Integration -----

class PipedriveIntegrationIn(Schema):
    api_key: str

class PipedriveIntegrationOut(Schema):
    is_configured: bool
    api_key_masked: Optional[str] = None
    is_active: bool
    updated_at: Optional[str] = None
    webhook_secret: Optional[str] = None

    sync_contacts: bool = False
    auto_create_deal: bool = False
    auto_close_deal: bool = False
    deal_pipeline_id: Optional[int] = None
    deal_stage_id: Optional[int] = None

class PipedriveConfigIn(Schema):
    sync_contacts: bool = False
    auto_create_deal: bool = False
    auto_close_deal: bool = False
    deal_pipeline_id: Optional[int] = None
    deal_stage_id: Optional[int] = None

class PipedriveStageOut(Schema):
    id: int
    name: str

class PipedrivePipelineOut(Schema):
    id: int
    name: str
    stages: list[PipedriveStageOut] = []

class MoveStageIn(Schema):
    stage_id: int

class QueueMemberIn(Schema):
    user_id: int
    percentage: int

class QueueIn(Schema):
    is_active: bool = True
    members: list[QueueMemberIn]

class QueueMemberOut(Schema):
    user_id: int
    user_name: str
    percentage: int
    assignment_count: int

class QueueOut(Schema):
    id: int
    is_active: bool
    members: list[QueueMemberOut]

