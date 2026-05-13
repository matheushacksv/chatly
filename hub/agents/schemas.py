from ninja import Schema
from typing import Optional
from datetime import datetime

class AIProviderIn(Schema):
    provider_type: str
    api_key: str

class AIProviderOut(Schema):
    id: int
    provider_type: str
    is_active: bool

class AIAgentIn(Schema):
    name: str
    description: str
    system_prompt: str
    model_name: str
    provider_id: int
    is_active: bool = True
    enabled_tools: list[str] = []
    memory_enabled: bool = False
    memory_type: str = 'per_contact'
    follow_up_enabled: bool = False
    follow_up_delay: int = 60
    max_follow_ups: int = 3
    follow_up_prompt: str = ''
    follow_up_respect_hours: bool = False
    goal_enabled: bool = False
    goal_description: str = ''
    goal_slots: list[dict] = []
    goal_action: str = ''
    goal_assign_to_id: Optional[int] = None
    goal_final_message: str = ''

class AIAgentOut(Schema):
    id: int
    name: str
    description: str
    system_prompt: str
    model_name: str
    is_active: bool
    provider: AIProviderOut
    enabled_tools: list[str] = []
    memory_enabled: bool = False
    memory_type: str = 'per_contact'
    follow_up_enabled: bool
    follow_up_delay: int
    max_follow_ups: int
    follow_up_prompt: str
    follow_up_respect_hours: bool
    goal_enabled: bool = False
    goal_description: str = ''
    goal_slots: list[dict] = []
    goal_action: str = ''
    goal_assign_to_id: Optional[int] = None
    goal_final_message: str = ''

class GoalCompletionOut(Schema):
    id: int
    conversation_id: int
    contact_id: int
    collected_data: dict
    reason: str
    created_at: datetime

class AgentDocumentOut(Schema):
    id: int
    name: str
    file_url: str
    status: str
    created_at: datetime


class AgentMembershipOut(Schema):
    id: int
    user_id: int
    agent_id: int
    assigned_at: datetime

class AgentMembershipIn(Schema):
    user_id: int

class AgentCustomToolIn(Schema):
    name: str
    description: str
    method: str
    url: str
    headers: dict = {}
    body_template: str = ''

class AgentCustomToolOut(Schema):
    id: int
    name: str
    description: str
    method: str
    url: str
    headers: dict = {}
    body_template: str
    is_active: bool
    created_at: datetime

    @staticmethod
    def resolve_headers(obj):
        import json
        try:
            return json.loads(obj.headers or '{}')
        except Exception:
            return {}
