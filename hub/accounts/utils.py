from accounts.models import User

def is_owner_or_admin(user):
    return user.role in (User.Role.OWNER, User.Role.ADMIN)

def has_permission(user, perm: str) -> bool:
    """Owners e admins têm todas as permissões; members verificam o grupo."""
    if is_owner_or_admin(user):
        return True
    if user.permission_group:
        return getattr(user.permission_group, perm, False)
    return False