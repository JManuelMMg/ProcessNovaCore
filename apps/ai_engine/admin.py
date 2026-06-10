from django.contrib import admin
from .models import Conversation, Message, Forecast, Anomaly, Recommendation


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'created_at', 'organization')
    list_filter = ('organization', 'created_at')
    search_fields = ('user__username', 'title')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'role', 'created_at', 'organization')
    list_filter = ('organization', 'role', 'created_at')
    search_fields = ('content',)


@admin.register(Forecast)
class ForecastAdmin(admin.ModelAdmin):
    list_display = ('type', 'period_start', 'period_end', 'organization', 'created_at')
    list_filter = ('organization', 'type', 'period_start')


@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    list_display = ('type', 'detected_at', 'resolved', 'organization')
    list_filter = ('organization', 'type', 'resolved', 'detected_at')
    search_fields = ('description',)


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'priority', 'action_taken', 'organization', 'created_at')
    list_filter = ('organization', 'category', 'priority', 'action_taken')
    search_fields = ('title', 'description')

