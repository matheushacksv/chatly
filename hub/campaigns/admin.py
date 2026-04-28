from django.contrib import admin
from .models import Campaign, CampaignMessage, CampaignContact


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name',)


admin.site.register(CampaignMessage)
admin.site.register(CampaignContact)
