from django.contrib import admin
from .models import Organization, PermissionGroup, User, Invite, BusinessHours, OrganizationMembership


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'organization', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'organization')
    search_fields = ('email', 'name')


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role')
    list_filter = ('role',)
    search_fields = ('user__email', 'organization__name')


@admin.register(PermissionGroup)
class PermissionGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization')
    search_fields = ('name',)


@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'organization', 'role', 'accepted', 'created_at')
    list_filter = ('accepted', 'role')
    search_fields = ('email',)


admin.site.register(BusinessHours)
