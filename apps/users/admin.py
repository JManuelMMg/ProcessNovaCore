from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import transaction
from .models import (
    Organization, Branch, Role, User, Membership, UserInvitation,
    AuditLog, Session
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'rfc', 'razon_social', 'city', 'state', 'is_active', 'created_at')
    search_fields = ('name', 'rfc', 'razon_social', 'email')

    def delete_queryset(self, request, queryset):
        """Optimizamos la eliminación de organizaciones para evitar timeouts"""
        from django.contrib.admin.models import LogEntry
        from django.contrib.contenttypes.models import ContentType
        
        # Desactivamos auditlog temporalmente para bulk deletes
        try:
            import auditlog
            auditlog.disable()
        except ImportError:
            pass
        
        try:
            for org in queryset:
                with transaction.atomic():
                    # Eliminamos registros de log primero para reducir memoria
                    ContentType.objects.get_for_model(Organization)
                    LogEntry.objects.filter(
                        content_type_id=ContentType.objects.get_for_model(Organization).id,
                        object_id=org.id
                    ).delete()
                    # Eliminamos la organización
                    org.delete()
        finally:
            # Reactivamos auditlog
            try:
                import auditlog
                auditlog.enable()
            except ImportError:
                pass


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'state', 'organization', 'is_main', 'is_active', 'manager')
    list_filter = ('organization', 'is_active', 'is_main')
    search_fields = ('name', 'city', 'state')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_system', 'is_active', 'organization')
    list_filter = ('organization', 'is_system', 'is_active')
    search_fields = ('name', 'description')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'phone', 
        'two_factor_enabled', 'is_staff', 'is_active'
    )
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': (
                'phone', 'mobile', 'avatar', 'bio', 'language', 'timezone',
                'two_factor_enabled', 'two_factor_secret', 'last_login_ip', 
                'last_login_agent', 'email_verified_at'
            )
        }),
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'language')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'branch', 'role', 'custom_role', 'is_active', 'joined_at')
    list_filter = ('role', 'organization', 'is_active')
    search_fields = ('user__username', 'user__email', 'organization__name')


@admin.register(UserInvitation)
class UserInvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'organization', 'role', 'accepted', 'expires_at', 'created_at')
    list_filter = ('organization', 'role', 'accepted')
    search_fields = ('email', 'first_name', 'last_name')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_repr', 'ip_address', 'created_at', 'organization')
    list_filter = ('organization', 'action', 'model_name', 'created_at')
    search_fields = ('user__username', 'model_name', 'object_repr', 'notes')
    readonly_fields = ('created_at',)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'location', 'is_active', 'created_at', 'last_activity_at', 'organization')
    list_filter = ('organization', 'is_active', 'created_at')
    search_fields = ('user__username', 'ip_address', 'location')
