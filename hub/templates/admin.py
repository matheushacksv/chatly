from django.contrib import admin
from .models import MessageTemplate


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'created_at')
    search_fields = ('title',)
