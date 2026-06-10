from django.contrib import admin
from .models import Segment, Lead, Customer, Opportunity, Campaign, Interaction


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'created_at')
    list_filter = ('organization',)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'status', 'source', 'score', 'assigned_to', 'organization', 'created_at')
    list_filter = ('organization', 'status', 'source', 'created_at')
    search_fields = ('name', 'email', 'phone', 'company')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'segment', 'score', 'total_orders', 'organization', 'created_at')
    search_fields = ('name', 'email', 'phone', 'rfc')
    list_filter = ('organization', 'segment', 'created_at')


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer', 'stage', 'amount', 'probability', 'assigned_to', 'organization', 'created_at')
    list_filter = ('organization', 'stage', 'created_at')
    search_fields = ('name', 'customer__name')


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'status', 'budget', 'leads_generated', 'conversions', 'organization', 'created_at')
    list_filter = ('organization', 'type', 'status', 'created_at')
    search_fields = ('name', 'description')


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'lead', 'opportunity', 'type', 'created_by', 'created_at', 'organization')
    list_filter = ('organization', 'type', 'created_at')
    search_fields = ('customer__name', 'lead__name', 'notes')

