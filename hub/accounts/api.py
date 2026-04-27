from accounts.models import OrganizationMembership
from django.core.files.storage import default_storage
from ninja.files import UploadedFile
from accounts.schemas import RegisterIn, UserOut, LoginIn, TokenOut, UpdateMeIn, AcceptInviteIn, RefreshIn, SwitchOrgIn, ForgotPasswordIn, ResetPasswordIn
from ninja import Router, File
from .models import Organization, User, Invite
from core.utils.errors import ErrorWithCodeSchema
from ninja_jwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
import uuid
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404


router = Router(tags=['Auth'])

@router.post('/register', response={201: TokenOut, 400: ErrorWithCodeSchema}, auth=None)
def register(request, data: RegisterIn):
    if User.objects.filter(email=data.email).exists():
        return 400, ErrorWithCodeSchema(detail='Email already in use', code='email_already_in_use')

    if Organization.objects.filter(slug=data.org_slug).exists():
        return 400, ErrorWithCodeSchema(detail='Slug already in use', code='slug_already_in_use')

    org = Organization.objects.create(name=data.org_name, slug=data.org_slug)
    user = User.objects.create_user(email=data.email, password=data.password, name=data.name, organization=org, role=User.Role.OWNER)

    refresh = RefreshToken.for_user(user)
    return 201, TokenOut(access=str(refresh.access_token), refresh=str(refresh))

@router.post('/login', response={200: TokenOut, 401: ErrorWithCodeSchema}, auth=None)
def login(request, data: LoginIn):
    user = authenticate(request, username=data.email, password=data.password)

    if not user:
        return 401, ErrorWithCodeSchema(detail='Invalid email or password', code='invalid_email_or_password')

    refresh = RefreshToken.for_user(user)

    return 200, TokenOut(access=str(refresh.access_token), refresh=str(refresh))

@router.post('/refresh', response={200: TokenOut, 401: ErrorWithCodeSchema}, auth=None)
def refresh_token(request, data: RefreshIn):
    try:
        refresh = RefreshToken(data.refresh)
        return 200, TokenOut(access=str(refresh.access_token), refresh=str(refresh))
    except Exception:
        return 401, ErrorWithCodeSchema(detail='Invalid or expired refresh token', code='invalid_refresh_token')


@router.get('/me', response=UserOut)
def me(request):
    return User.objects.select_related('permission_group', 'organization').get(id=request.auth.id)


@router.put('/me', response=UserOut)
def update_me(request, data: UpdateMeIn):
    user = request.auth

    if data.new_password:
        if not user.check_password(data.current_password):
            return 400, ErrorWithCodeSchema(detail='Incorrect password', code='incorrect_password')
        user.set_password(data.new_password)
    
    if data.name:
        user.name = data.name
    
    user.save()
    return user
        
@router.patch('/avatar', response={200: UserOut})
def upload_avatar(request, file: UploadedFile = File(...)):
    user = request.auth

    mime = file.content_type or 'application/octet-stream'
    ext = mime.split('/')[-1].split(';')[0]
    path = default_storage.save(
        f'avatars/{uuid.uuid4()}.{ext}',
        ContentFile(file.read())
    )

    url = default_storage.url(path)

    user.avatar = url
    user.save()

    return 200, user

#* ----- Accept Invite ------

@router.post('/invite/accept', response={200: TokenOut, 201: TokenOut, 400: ErrorWithCodeSchema}, auth=None)
def accept_invite(request, data: AcceptInviteIn):

    invite = get_object_or_404(Invite, token=data.token)
    if not invite.is_valid():
        return 400, ErrorWithCodeSchema(detail='Invalid or expired invite', code='invalid_invite')

    existing_user = User.objects.filter(email=invite.email).first()

    if existing_user:
        OrganizationMembership.objects.get_or_create(
            user=existing_user,
            organization=invite.organization,
            defaults={'role': invite.role, 'permission_group': invite.permission_group}
        )
        invite.accepted = True
        invite.save()
        refresh = RefreshToken.for_user(existing_user)
        return 200, TokenOut(access=str(refresh.access_token), refresh=str(refresh))
    else:
        user = User.objects.create_user(
            email=invite.email,
            password=data.password,
            name=data.name,
            organization=invite.organization,
            role=invite.role,
            permission_group=invite.permission_group,
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=invite.organization,
            role=invite.role,
            permission_group=invite.permission_group
        )
        invite.accepted = True
        invite.save()
        refresh = RefreshToken.for_user(user)
        return 201, TokenOut(access=str(refresh.access_token), refresh=str(refresh))

#* ----- Orgs -----

@router.get('/my-orgs')
def my_orgs(request):
    memberships = OrganizationMembership.objects.filter(user=request.auth).select_related('organization')
    return [
        {
            'id': m.organization.id,
            'name': m.organization.name,
            'slug': m.organization.slug,
            'role': m.role,
            'is_active': m.organization.id == request.auth.organization_id,
        }
        for m in memberships
    ]

@router.post('/switch-org')
def switch_org(request, data: SwitchOrgIn):

    membership = get_object_or_404(OrganizationMembership, user=request.auth, organization_id=data.org_id)

    user = request.auth
    user.organization_id = data.org_id
    user.role = membership.role
    user.permission_group = membership.permission_group
    user.save(update_fields=['organization_id', 'role', 'permission_group'])

    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


#* ----- Password Reset -----

@router.post('/forgot-password', response={200: dict}, auth=None)
def forgot_password(request, data: ForgotPasswordIn):
    user = User.objects.filter(email=data.email).first()
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
        send_mail(
            subject='Redefinição de senha — ChatlyAi',
            message=f'Acesse o link para redefinir sua senha: {reset_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=f'<p>Clique no link para redefinir sua senha:</p><p><a href="{reset_url}">{reset_url}</a></p><p>O link expira em 24 horas.</p>',
            fail_silently=True,
        )
    # Sempre retorna 200 para não revelar se o email existe
    return 200, {'detail': 'Se o email existir, você receberá um link em breve.'}


@router.post('/reset-password', response={200: dict, 400: ErrorWithCodeSchema}, auth=None)
def reset_password(request, data: ResetPasswordIn):
    try:
        uid = force_str(urlsafe_base64_decode(data.uid))
        user = User.objects.get(pk=uid)
    except Exception:
        return 400, ErrorWithCodeSchema(detail='Token inválido', code='invalid_token')

    if not default_token_generator.check_token(user, data.token):
        return 400, ErrorWithCodeSchema(detail='Token inválido ou expirado', code='invalid_token')

    user.set_password(data.password)
    user.save()
    return 200, {'detail': 'Senha redefinida com sucesso.'}