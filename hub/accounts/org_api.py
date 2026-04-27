from django.shortcuts import get_object_or_404
from accounts.models import OrganizationMembership
from ninja import Router
from core.utils.errors import ErrorWithCodeSchema, GenericErrorSchema
from .models import User, PermissionGroup, Invite, BusinessHours
from .schemas import MemberOut, UpdateMemberIn, PermissionGroupIn, PermissionsGroupOut, InviteIn, OrgSettingsIn, OrgSettingsOut, BusinessHoursIn, BusinessHoursOut
from django.utils import timezone
from datetime import timedelta
from .tasks import send_invite_email
from accounts.utils import is_owner_or_admin
from integrations.schemas import PipedriveIntegrationIn, PipedriveIntegrationOut, PipedriveConfigIn, PipedrivePipelineOut
from integrations.models import PipedriveIntegration
from accounts.utils import has_permission
from integrations.pipedrive_services import validate_integration, pipeline_with_stages

router = Router(tags=['Organization'])


@router.patch('/settings', response={200: OrgSettingsOut, 403: ErrorWithCodeSchema})
def update_org_settings(request, data: OrgSettingsIn):
    if request.auth.role != User.Role.OWNER:
        return 403, ErrorWithCodeSchema(detail='Only owners can update organization settings', code='no_permission')
    org = request.auth.organization
    org.name = data.name
    org.save()
    return org

#* ------ Members Endpoints ------

@router.get('/members', response=list[MemberOut])
def list_members(request):
    return User.objects.filter(organization=request.auth.organization)

@router.patch('/members/{member_id}', response={200: MemberOut, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def update_member(request, member_id: int, data: UpdateMemberIn):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')
    
    try:
        member = User.objects.get(id=member_id, organization=request.auth.organization)
    except User.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Member not found', code='member_not_found')

    membership, _ = OrganizationMembership.objects.get_or_create(user=member, organization=request.auth.organization, defaults={'role': member.role, 'permission_group': member.permission_group})

    if data.role:
        member.role = data.role
        if membership:
            membership.role = data.role
    if data.permission_group_id is not None:
        try:
            group = PermissionGroup.objects.get(id=data.permission_group_id, organization=request.auth.organization)
        except PermissionGroup.DoesNotExist:
            return 404, ErrorWithCodeSchema(detail='Group not found', code='group_not_found')
        member.permission_group = group
        membership.permission_group = group

    membership.save()
    member.save()
    return member

@router.delete('/member/{member_id}', response={204: None, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def remove_member(request, member_id: int):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    try:
        member = User.objects.get(id=member_id, organization=request.auth.organization)
    except User.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Member not found', code='member_not_found')

    get_object_or_404(OrganizationMembership, user=member, organization=request.auth.organization).delete()
    
    if member.organization_id == request.auth.organization.id:
        other = OrganizationMembership.objects.filter(user=member).first()
        member.organization = other.organization if other else None
        member.role = other.role if other else 'member'
        member.permission_group = other.permission_group if other else None
        member.save()

    return 204, None

#* ------ Permission Groups Endpoints ------

@router.get('/permission-groups', response=list[PermissionsGroupOut])
def list_permission_groups(request):
    return PermissionGroup.objects.filter(organization=request.auth.organization)

@router.post('/permission-groups', response={201: PermissionsGroupOut, 403: ErrorWithCodeSchema})
def create_permission_group(request, data: PermissionGroupIn):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    group = PermissionGroup.objects.create(organization=request.auth.organization, **data.dict())
    return 201, group

@router.put('/permission-groups/{group_id}', response={200: PermissionsGroupOut, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def update_permission_group(request, group_id: int, data: PermissionGroupIn):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')
    
    try:
        group = PermissionGroup.objects.get(id=group_id, organization=request.auth.organization)
    except PermissionGroup.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Group not found', code='group_not_found')

    for field, value in data.dict().items():
        setattr(group, field, value)
    group.save()
    return group

@router.delete('/permission-groups/{group_id}', response={204: None, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def delete_permission_group(request, group_id: int):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    try:
        group = PermissionGroup.objects.get(id=group_id, organization=request.auth.organization)
    except PermissionGroup.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Group not found', code='group_not_found')

    group.delete()
    return 204, None

#* ------ Invites Endpoints ------

@router.post('/invites', response={201: None, 403: ErrorWithCodeSchema, 400: ErrorWithCodeSchema})
def create_invite(request, data: InviteIn):
    if not is_owner_or_admin(request.auth):
        return 403, ErrorWithCodeSchema(detail='No permission', code='no_permission')

    from billing.services import check_member_limit
    if not check_member_limit(request.auth.organization):
        return 400, ErrorWithCodeSchema(detail='Limite de membros atingido no plano atual', code='member_limit_reached')

    if User.objects.filter(email=data.email, organization=request.auth.organization).exists():
        return 400, ErrorWithCodeSchema(detail='User already member', code='user_already_member')

    if Invite.objects.filter(email=data.email, organization=request.auth.organization, accepted=False).exists():
        return 400, ErrorWithCodeSchema(detail='Invite already exists for this email', code='invite_already_exists')

    permission_group = None
    if data.permission_group_id:
        try:
            permission_group = PermissionGroup.objects.get(
                id=data.permission_group_id,
                organization=request.auth.organization
            )
        except PermissionGroup.DoesNotExist:
            return 400, ErrorWithCodeSchema(detail='Group not found', code='group_not_found')

    invite = Invite.objects.create(
        organization=request.auth.organization,
        email=data.email,
        role=data.role,
        permission_group=permission_group,
        invited_by=request.auth,
        expires_at=timezone.now() + timedelta(days=7)
    )

    send_invite_email.delay(invite.id)

    return 201, None

#* ------ Pipedrive Integration Endpoints ------

def _mask_key(key: str) -> str:
    return '****' + key[-4:] if len(key) >= 4 else '****'

@router.get('/integrations/pipedrive/pipelines', response=list[PipedrivePipelineOut])
def get_pipedrive_pipelines(request):
    if not is_owner_or_admin(request.auth):
        return []
    try:
        integration = PipedriveIntegration.objects.get(organization=request.auth.organization)
        return pipeline_with_stages(integration.api_key)
    except PipedriveIntegration.DoesNotExist:
        return []

@router.get('/integrations/pipedrive', response={200: PipedriveIntegrationOut, 403: GenericErrorSchema})
def get_pipedrive_integration(request):
    '''Retorna status da integração'''

    if not has_permission(request.auth, 'view_pipedriveintegration'):
        return 403, GenericErrorSchema(detail='No permission')

    try:
        integration = PipedriveIntegration.objects.get(organization=request.auth.organization)
        return PipedriveIntegrationOut(
            is_configured=True,
            api_key_masked=_mask_key(integration.api_key),
            is_active=integration.is_active,
            updated_at=integration.updated_at.isoformat(),
            webhook_secret=str(integration.webhook_secret),
            sync_contacts=integration.sync_contacts,
            auto_create_deal=integration.auto_create_deal,
            auto_close_deal=integration.auto_close_deal,
            deal_pipeline_id=integration.deal_pipeline_id,
            deal_stage_id=integration.deal_stage_id,
        )
    except PipedriveIntegration.DoesNotExist:
        return PipedriveIntegrationOut(is_configured=False, is_active=False)

@router.put('/integrations/pipedrive', response={200: PipedriveIntegrationOut, 400: GenericErrorSchema, 403: GenericErrorSchema})
def save_pipedrive_integration(request, data: PipedriveIntegrationIn):
    '''Salva ou atualiza a API key. Valida com Pipedrive antes de persistir'''

    if not has_permission(request.auth, 'add_pipedriveintegration'):
        return 403, GenericErrorSchema(detail='No permission')

    validation = validate_integration(data.api_key)

    if not validation:
        return 400, GenericErrorSchema(detail='Invalid API Key or Pipedrive unreachable')
    
    integration, _ = PipedriveIntegration.objects.update_or_create(
        organization=request.auth.organization,
        defaults={'api_key': data.api_key, 'is_active': True}
    )

    return PipedriveIntegrationOut(
        is_configured=True,
        api_key_masked=_mask_key(integration.api_key),
        is_active=True,
        updated_at=integration.updated_at.isoformat(),
        webhook_secret=str(integration.webhook_secret),
        sync_contacts=integration.sync_contacts,
        auto_create_deal=integration.auto_create_deal,
        auto_close_deal=integration.auto_close_deal,
        deal_pipeline_id=integration.deal_pipeline_id,
        deal_stage_id=integration.deal_stage_id,
    )

@router.patch('/integrations/pipedrive/config', response={200: PipedriveIntegrationOut, 403: ErrorWithCodeSchema, 404: ErrorWithCodeSchema})
def update_pipedrive_config(request, data: PipedriveConfigIn):
    if request.auth.role != User.Role.OWNER:
        return 403, ErrorWithCodeSchema(detail='Only owners can update integration config', code='no_permission')
    try:
        integration = PipedriveIntegration.objects.get(organization=request.auth.organization)
    except PipedriveIntegration.DoesNotExist:
        return 404, ErrorWithCodeSchema(detail='Integration not configured', code='not_found')

    for field, value in data.dict().items():
        setattr(integration, field, value)
    integration.save()

    return PipedriveIntegrationOut(
        is_configured=True,
        api_key_masked=_mask_key(integration.api_key),
        is_active=integration.is_active,
        updated_at=integration.updated_at.isoformat(),
        webhook_secret=str(integration.webhook_secret),
        sync_contacts=integration.sync_contacts,
        auto_create_deal=integration.auto_create_deal,
        auto_close_deal=integration.auto_close_deal,
        deal_pipeline_id=integration.deal_pipeline_id,
        deal_stage_id=integration.deal_stage_id,
    )

@router.delete('/integrations/pipedrive', response={204: None, 403: GenericErrorSchema, 404: GenericErrorSchema})
def delete_pipedrive_integration(request):
    '''Remove a integração da organização'''

    if not has_permission(request.auth, 'delete_pipedriveintegration'):
        return 403, GenericErrorSchema(detail='No permission')

    try:
        PipedriveIntegration.objects.get(organization=request.auth.organization).delete()
        return 204, None
    except PipedriveIntegration.DoesNotExist:
        return 404, GenericErrorSchema(detail='Integration not found')

#* ----- Business Hours endpoints -----

@router.get('/business-hours/', response=list[BusinessHoursOut])
def get_business_hours(request):
    org = request.auth.organization

    defaults = [
        {'is_open': i < 5, 'open_time': '09:00', 'close_time': '18:00'}
        for i in range(7)
    ]
    for i, d in enumerate(defaults):
        BusinessHours.objects.get_or_create(organization=org, weekday=i, defaults=d)
    return BusinessHours.objects.filter(organization=org)

@router.put('/business-hours/', response=list[BusinessHoursOut])
def update_business_hours(request, data: list[BusinessHoursIn]):
    org = request.auth.organization

    for row in data:
        BusinessHours.objects.filter(organization=org, weekday=row.weekday).update(
            is_open=row.is_open, open_time=row.open_time, close_time=row.close_time
        )
    return BusinessHours.objects.filter(organization=org)

