from enum import auto
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid


class Organization(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email é orbigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class PermissionGroup(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    can_view_agents = models.BooleanField(default=False)
    can_create_agents = models.BooleanField(default=False)
    can_edit_agents = models.BooleanField(default=False)
    can_delete_agents = models.BooleanField(default=False)
    can_view_conversations = models.BooleanField(default=False)
    can_delete_conversations = models.BooleanField(default=False)
    can_export_conversations = models.BooleanField(default=False)
    
    #* Pipedrive Integration
    view_pipedriveintegration = models.BooleanField(default=False)
    add_pipedriveintegration = models.BooleanField(default=False)
    delete_pipedriveintegration = models.BooleanField(default=False)

class User(AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'

    name = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    avatar = models.URLField(blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='users')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    permission_group = models.ForeignKey(PermissionGroup, null=True, blank=True, on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email
    

class Invite(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invites')
    email = models.EmailField()    
    role = models.CharField(max_length=10, choices=User.Role.choices, default=User.Role.MEMBER)
    permission_group = models.ForeignKey(PermissionGroup, null=True, blank=True, on_delete=models.SET_NULL)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invites')
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        from django.utils import timezone
        return not self.accepted and self.expires_at > timezone.now()


class BusinessHours(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='business_hours')
    weekday = models.PositiveSmallIntegerField()
    is_open = models.BooleanField(default=True)
    open_time = models.TimeField(default='09:00')
    close_time = models.TimeField(default='18:00')

    class Meta:
        unique_together = ('organization', 'weekday')
        ordering = ['weekday']

class OrganizationMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=User.Role.choices, default=User.Role.MEMBER)
    permission_group = models.ForeignKey(PermissionGroup, on_delete=models.SET_NULL, null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'organization')
