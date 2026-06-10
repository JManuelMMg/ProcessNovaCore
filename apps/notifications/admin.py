from django.contrib import admin
from .models import NotificationTemplate, NotificationPreference, Notification, NotificationLog


class NotificationLogInline(admin.TabularInline):
    model = NotificationLog
    extra = 0


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'is_active', 'language', 'organization')
    list_filter = ('organization', 'type', 'is_active', 'language')
    search_fields = ('name', 'subject', 'content')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'updated_at')
    list_filter = ('organization',)
    search_fields = ('user__username', 'user__email')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'customer', 'employee', 'channel', 'priority', 'status', 'scheduled_at', 'created_at', 'organization')
    list_filter = ('organization', 'channel', 'status', 'priority', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'customer__name', 'employee__first_name', 'employee__last_name')
    inlines = [NotificationLogInline]

