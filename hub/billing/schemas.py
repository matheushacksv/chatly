from ninja import Schema
from typing import Optional
from decimal import Decimal

class PlanOut(Schema):
    id: int
    name: str
    slug: str
    base_price: Decimal
    extra_instance_price: Decimal
    max_instances: Optional[int]
    max_members: Optional[int]
    max_contacts: Optional[int]
    is_unlimited: bool
    sort_order: int
    stripe_price_id: Optional[str] = None

class UsageOut(Schema):
    instances_used: int
    members_used: int
    contacts_used: int

class SubscriptionOut(Schema):
    plan: PlanOut
    status: str
    extra_instances: int
    max_instances_total: Optional[int]
    current_period_end: Optional[str]
    usage: UsageOut

class CheckoutIn(Schema):
    plan_slug: str
    success_url: str
    cancel_url: str

class PortalIn(Schema):
    return_url: str

class ExtraInstancesIn(Schema):
    quantity: int

class AssignPlanIn(Schema):
    plan_slug: str
    granted_by_id: Optional[int] = None

class AdminOrgOut(Schema):
    id: int
    name: str
    slug: str
    plan_name: str
    plan_slug: str
    status: str
    extra_instances: int




