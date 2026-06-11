from ninja import Schema
from pydantic import EmailStr, Field, model_validator
from typing import Optional, Annotated, Self
from datetime import time

# Auth Schemas

class ApiKeyOut(Schema):
    api_key: Optional[str] = None

class RefreshIn(Schema):
    refresh: str

class RegisterIn(Schema):
    org_name: str
    org_slug: str
    name: Optional[str] = None
    email: EmailStr
    password: Annotated[str, Field(min_length=8)]
    repeat_password: str

    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        if self.password != self.repeat_password:
            raise ValueError('Passwords do not match')
        return self

class UserPermissionsOut(Schema):
    can_view_agents: bool = False
    can_create_agents: bool = False
    can_edit_agents: bool = False
    can_delete_agents: bool = False
    can_view_conversations: bool = False
    can_delete_conversations: bool = False
    can_export_conversations: bool = False
    view_pipedriveintegration: bool = False
    add_pipedriveintegration: bool = False
    delete_pipedriveintegration: bool = False

class UserOut(Schema):
    id: int
    name: Optional[str] = None
    email: str
    role: str
    org_name: Optional[str] = None
    avatar: Optional[str] = None
    permissions: UserPermissionsOut = UserPermissionsOut()

    @staticmethod
    def resolve_org_name(obj):
        return obj.organization.name if obj.organization else None

    @staticmethod
    def resolve_permissions(obj):
        if obj.role in ('owner', 'admin'):
            return UserPermissionsOut(
                can_view_agents=True,
                can_create_agents=True,
                can_edit_agents=True,
                can_delete_agents=True,
                can_view_conversations=True,
                can_delete_conversations=True,
                can_export_conversations=True,
                view_pipedriveintegration=True,
                add_pipedriveintegration=True,
                delete_pipedriveintegration=True,
            )
        if obj.permission_group:
            pg = obj.permission_group
            return UserPermissionsOut(
                can_view_agents=pg.can_view_agents,
                can_create_agents=pg.can_create_agents,
                can_edit_agents=pg.can_edit_agents,
                can_delete_agents=pg.can_delete_agents,
                can_view_conversations=pg.can_view_conversations,
                can_delete_conversations=pg.can_delete_conversations,
                can_export_conversations=pg.can_export_conversations,
                view_pipedriveintegration=pg.view_pipedriveintegration,
                add_pipedriveintegration=pg.add_pipedriveintegration,
                delete_pipedriveintegration=pg.delete_pipedriveintegration,
            )
        return UserPermissionsOut()

class LoginIn(Schema):
    email: EmailStr
    password: str

class TokenOut(Schema):
    access: str
    refresh: str

class UpdateMeIn(Schema):
    name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

    @model_validator(mode='after')
    def check_password_fields(self) -> Self:
        if self.new_password and not self.current_password:
            raise ValueError('To change your password, inform your actual password')
        return self


# Permissions Schemas

class PermissionGroupIn(Schema):
    name: str
    can_view_agents: bool = False
    can_create_agents: bool = False
    can_edit_agents: bool = False
    can_delete_agents: bool = False
    can_view_conversations: bool = False
    can_delete_conversations: bool = False
    can_export_conversations: bool = False
    view_pipedriveintegration: bool = False
    add_pipedriveintegration: bool = False
    delete_pipedriveintegration: bool = False

class PermissionsGroupOut(Schema):
    id: int
    name: str
    can_view_agents: bool
    can_create_agents: bool
    can_edit_agents: bool
    can_delete_agents: bool
    can_view_conversations: bool
    can_delete_conversations: bool
    can_export_conversations: bool
    view_pipedriveintegration: bool
    add_pipedriveintegration: bool
    delete_pipedriveintegration: bool

class MemberOut(Schema):
    id: int
    name: str
    email: str
    role: str
    permission_group: Optional[PermissionsGroupOut] = None

class UpdateMemberIn(Schema):
    role: Optional[str] = None
    permission_group_id: Optional[int] = None


# Invite Schemas

class OrgSettingsIn(Schema):
    name: str

class OrgSettingsOut(Schema):
    id: int
    name: str
    slug: str

class InviteIn(Schema):
    email: EmailStr
    role: str
    permission_group_id: Optional[int] = None

class AcceptInviteIn(Schema):
    token: str
    name: str
    password: Annotated[str, Field(min_length=8)]
    repeat_password: str

    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        if self.password != self.repeat_password:
            raise ValueError('Passwords do not match')
        return self

# Business Hours Schemas

class BusinessHoursIn(Schema):
    weekday: int
    is_open: bool
    open_time: str
    close_time: str

class BusinessHoursOut(Schema):
    weekday: int
    is_open: bool
    open_time: time
    close_time: time

# Orgs Schemas

class SwitchOrgIn(Schema):
    org_id: int

# Password Reset Schemas

class ForgotPasswordIn(Schema):
    email: EmailStr

class ResetPasswordIn(Schema):
    uid: str
    token: str
    password: Annotated[str, Field(min_length=8)]
    repeat_password: str

    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        if self.password != self.repeat_password:
            raise ValueError('Passwords do not match')
        return self