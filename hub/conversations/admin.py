from django.contrib import admin
from .models import Conversation, Message, MessageAttachment, Sticker


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'contact', 'organization', 'status', 'started_at')
    list_filter = ('status', 'organization')
    search_fields = ('contact__name', 'contact__phone')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('content',)


admin.site.register(MessageAttachment)
admin.site.register(Sticker)
