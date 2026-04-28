from django.contrib import admin
from .models import AIProvider, AIAgent, AgentDocument, AgentCustomTool, AgentMembership


@admin.register(AIProvider)
class AIProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'organization')
    list_filter = ('provider',)
    search_fields = ('name',)


@admin.register(AIAgent)
class AIAgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'is_active')
    list_filter = ('is_active', 'organization')
    search_fields = ('name',)


@admin.register(AgentDocument)
class AgentDocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'agent', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name',)


admin.site.register(AgentCustomTool)
admin.site.register(AgentMembership)
