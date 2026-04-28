from django.contrib import admin
from .models import Contact, ContactAnnotation


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'organization', 'created_at')
    list_filter = ('organization',)
    search_fields = ('name', 'phone', 'email')


admin.site.register(ContactAnnotation)
