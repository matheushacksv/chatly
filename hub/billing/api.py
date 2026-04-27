from ninja import Router
from django.shortcuts import get_object_or_404
from core.utils.errors import ErrorWithCodeSchema
from .models import Plan, OrganizationSubscription
from .schemas import PlanOut, SubscriptionOut, CheckoutIn, PortalIn, ExtraInstancesIn, AssignPlanIn, AdminOrgOut
from . import services
from integrations.models import WhatsAppInstance
from accounts.models import User, Organization
from contacts.models import Contact
import logging

logger = logging.getLogger(__name__)


router = Router(tags=['Billing'])
admin_router = Router(tags=['Admin Billing'])

def _build_subscription_out(sub, org):
    instances_used = WhatsAppInstance.objects.filter(organization=org).count()
    members_used = User.objects.filter(organization=org, is_active=True).count()
    contacts_used = Contact.objects.filter(organization=org).count()

    return {
        'plan': sub.plan,
        'status': sub.status,
        'extra_instances': sub.extra_instances,
        'max_instances_total': sub.max_instances_total,
        'current_period_end': sub.current_period_end.isoformat() if sub.current_period_end else None,
        'usage': {
            'instances_used': instances_used,
            'members_used': members_used,
            'contacts_used': contacts_used
        }
    }

@router.get('/', response=SubscriptionOut)
def get_subscription(request):
    org = request.auth.organization
    sub = services.get_or_create_subscription(org)
    return _build_subscription_out(sub, org)

@router.get('/plans', response=list[PlanOut])
def list_plans(request):
    return Plan.objects.filter(is_active=True).exclude(slug='unlimited')

@router.post('/checkout', response={200: dict, 400: ErrorWithCodeSchema})
def checkout(request, data: CheckoutIn):

    try:
        url = services.create_checkout_session(
            request.auth.organization, data.plan_slug, data.success_url, data.cancel_url
        )
        return 200, {'url': url}
    except Exception as e:
        logger.error(msg=f'Erro ao criar checkout: {e}')
        return 400, ErrorWithCodeSchema(detail=str(e), code='checkout_error')

@router.post('/portal', response={200: dict, 400: ErrorWithCodeSchema})
def portal(request, data: PortalIn):

    try:
        url = services.create_portal_session(request.auth.organization, data.return_url)
        return 200, {'url': url}
    except Exception as e:
        logger.error(msg=f'Erro ao criar portal: {e}')
        return 400, ErrorWithCodeSchema(detail=str(e), code='portal_error')

@router.post('/extra-instances', response={200: SubscriptionOut, 400: ErrorWithCodeSchema})
def add_extra_instances(request, data: ExtraInstancesIn):
    if data.quantity < 1:
        return 400, ErrorWithCodeSchema(detail='Quantidade inválida', code='invalid_quantity')

    org = request.auth.organization
    try:
        services.add_extra_instances(org, data.quantity)
        sub = services.get_or_create_subscription(org)
        return 200, _build_subscription_out(org, sub)
    except Exception as e:
        logger.error(msg=f'Erro ao adicionar extra_instances: {e}')
        return 400, ErrorWithCodeSchema(detail=str(e), code='extra_instance_error')

#* ----- Admin -----

@admin_router.get('/orgs', response=list[AdminOrgOut])
def admin_list_orgs(request):
    if not request.auth.is_superuser:
        return []
    
    orgs = Organization.objects.all().prefetch_related('subscription__plan')
    result = []

    for org in orgs:
        sub = getattr(org, 'subscription', None)
        result.append({
            'id': org.id,
            'name': org.name,
            'slug': org.slug,
            'plan_name': sub.plan.name if sub else 'Sem plano',
            'plan_slug': sub.plan.slug if sub else '',
            'status': sub.status if sub else 'free',
            'extra_instances': sub.extra_instances if sub else 0
        })
    return result

@admin_router.post('/orgs/{org_id}/plan', response={200: dict, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def admin_assign_plan(request, org_id: int, data: AssignPlanIn):
    if not request.auth.is_superuser:
        return 403, ErrorWithCodeSchema(detail='Acesso negado', code='forbidden')

    org = get_object_or_404(Organization, id=org_id)
    plan = get_object_or_404(Plan, slug=data.plan_slug)
    sub = services.get_or_create_subscription(org)
    sub.plan = plan
    sub.status = OrganizationSubscription.Status.ACTIVE
    if data.granted_by_id:
        try:
            sub.granted_by = User.objects.get(id=data.granted_by_id)
        except User.DoesNotExist:
            pass
    elif plan.is_unlimited:
        sub.granted_by = request.auth
    sub.save()
    return 200, {'detail': f'Plano {plan.name} atribuído a {org.name}'}


