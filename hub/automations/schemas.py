from datetime import datetime
from typing import Any, Optional
from ninja import Schema


class AutomationStepIn(Schema):
    order: int
    action_type: str
    config: dict = {}
    then_steps: list['AutomationStepIn'] = []
    else_steps: list['AutomationStepIn'] = []


class AutomationStepOut(Schema):
    id: int
    order: int
    action_type: str
    config: dict
    branch: str = ''
    then_steps: list['AutomationStepOut'] = []
    else_steps: list['AutomationStepOut'] = []

    @staticmethod
    def resolve_then_steps(obj):
        return [c for c in obj.children.all() if c.branch == 'then']
    
    @staticmethod
    def resolve_else_steps(obj):
        return [c for c in obj.children.all() if c.branch == 'else']


class AutomationIn(Schema):
    name: str
    trigger_type: str
    trigger_filters: dict = {}
    is_active: bool = False
    steps: list[AutomationStepIn] = []


class AutomationOut(Schema):
    id: int
    name: str
    trigger_type: str
    trigger_filters: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime
    steps: list[AutomationStepOut]

    @staticmethod
    def resolve_steps(obj):
        return [s for s in obj.steps.all() if s.parent_id is None]


class AutomationListOut(Schema):
    id: int
    name: str
    trigger_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    steps_count: int

    @staticmethod
    def resolve_steps_count(obj):
        return obj.steps.count()


class AutomationRunOut(Schema):
    id: int
    status: str
    context: dict
    current_step: int
    error: str
    started_at: datetime
    finished_at: Optional[datetime] = None


class ToggleIn(Schema):
    is_active: bool


class TriggerMeta(Schema):
    type: str
    label: str


class ActionFieldMeta(Schema):
    key: str
    label: str
    type: str
    required: bool = False
    options: Optional[list[dict]] = None


class ActionMeta(Schema):
    type: str
    label: str
    fields: list[ActionFieldMeta]
