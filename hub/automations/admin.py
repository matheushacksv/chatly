from django.contrib import admin
from .models import Automation, AutomationStep, AutomationRun


class AutomationStepInline(admin.TabularInline):
    model = AutomationStep
    extra = 0


@admin.register(Automation)
class AutomationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organization', 'trigger_type', 'is_active', 'created_at')
    list_filter = ('trigger_type', 'is_active', 'organization')
    search_fields = ('name',)
    inlines = [AutomationStepInline]


@admin.register(AutomationRun)
class AutomationRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'automation', 'status', 'current_step', 'started_at', 'finished_at')
    list_filter = ('status',)
    readonly_fields = ('automation', 'status', 'context', 'current_step', 'error', 'started_at', 'finished_at')
