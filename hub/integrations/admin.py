from django.contrib import admin
from .models import WhatsAppInstance, PipedriveIntegration, AssignmentQueue, AssignmentQueueMember


@admin.register(WhatsAppInstance)
class WhatsAppInstanceAdmin(admin.ModelAdmin):
    list_display = ('instance_name', 'organization', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('instance_name',)


admin.site.register(PipedriveIntegration)
admin.site.register(AssignmentQueue)
admin.site.register(AssignmentQueueMember)
