import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
from auditlog.registry import auditlog
from core.models import TenantAwareModel


class Organization(models.Model):
    name = models.CharField(max_length=255)
    rfc = models.CharField(max_length=13, unique=True)
    razon_social = models.CharField(max_length=255)
    regimen_fiscal = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='organizations/logos/', blank=True, null=True)
    currency = models.CharField(max_length=3, default='MXN', help_text='Moneda principal')
    timezone = models.CharField(max_length=50, default='America/Mexico_City')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Branch(TenantAwareModel):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    is_main = models.BooleanField(default=False)
    manager = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_branches'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sucursal'
        verbose_name_plural = 'Sucursales'
        unique_together = ['name', 'organization']

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class Role(TenantAwareModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=dict, blank=True, help_text='Permisos del rol')
    is_system = models.BooleanField(default=False, help_text='Rol de sistema (no editable)')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'organization']

    def __str__(self):
        return self.name


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='users/avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    language = models.CharField(max_length=10, default='es')
    timezone = models.CharField(max_length=50, default='America/Mexico_City')
    two_factor_enabled = models.BooleanField(default=False, help_text='Autenticación de dos factores activada')
    two_factor_secret = models.CharField(max_length=100, blank=True, help_text='Secreto para 2FA')
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_login_agent = models.TextField(blank=True)
    email_verified_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

    @property
    def role(self):
        try:
            return self.membership.role
        except Membership.DoesNotExist:
            return 'employee'

    @property
    def role_display(self):
        return dict(Membership.ROLE_CHOICES).get(self.role, self.role)


class Membership(models.Model):
    ROLE_CHOICES = [
        ('admin_central', 'Administrador Central'),
        ('branch_manager', 'Encargado de Sucursal'),
        ('employee', 'Empleado'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='membership')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='members', help_text='Sucursal asignada (vacío para admin central)'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    custom_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='memberships')
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.get_role_display()})"


class UserInvitation(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Membership.ROLE_CHOICES, default='employee')
    custom_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invitations')
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitación a {self.email}"

    @property
    def is_valid(self):
        return not self.accepted and self.expires_at > timezone.now()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)


class AuditLog(TenantAwareModel):
    ACTION_CHOICES = [
        ('create', 'Crear'),
        ('update', 'Actualizar'),
        ('delete', 'Eliminar'),
        ('login', 'Inicio de sesión'),
        ('logout', 'Cierre de sesión'),
        ('view', 'Ver'),
        ('export', 'Exportar'),
        ('other', 'Otro'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='other')
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    request_path = models.CharField(max_length=255, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.user or 'Sistema'} - {self.get_action_display()} - {self.created_at}"


class Session(TenantAwareModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    location = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.ip_address or 'Unknown IP'}"


auditlog.register(Organization)
auditlog.register(Branch)
auditlog.register(Role)
auditlog.register(User)
auditlog.register(Membership)
auditlog.register(UserInvitation)
auditlog.register(AuditLog)
auditlog.register(Session)
