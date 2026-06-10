from django.db import models
from core.models import TenantAwareModel
from auditlog.registry import auditlog


class NotificationTemplate(TenantAwareModel):
    TYPE_CHOICES = [
        ('email', 'Email'),
        ('push', 'Push'),
        ('sms', 'SMS'),
        ('in_app', 'En aplicación'),
        ('whatsapp', 'WhatsApp'),
    ]

    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    subject = models.CharField(max_length=500, blank=True, help_text='Asunto para emails')
    content = models.TextField(help_text='Contenido de la plantilla (usa {{ variable }} para placeholders)')
    html_content = models.TextField(blank=True, help_text='Contenido HTML para emails')
    variables = models.JSONField(default=list, blank=True, help_text='Variables disponibles en la plantilla')
    is_active = models.BooleanField(default=True)
    language = models.CharField(max_length=10, default='es', help_text='Código de idioma (es, en, etc.)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class NotificationPreference(TenantAwareModel):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='notification_preferences')
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    whatsapp_enabled = models.BooleanField(default=False)
    order_updates = models.BooleanField(default=True, help_text='Actualizaciones de pedidos')
    sales_reminders = models.BooleanField(default=True, help_text='Recordatorios de ventas')
    inventory_alerts = models.BooleanField(default=True, help_text='Alertas de inventario')
    finance_alerts = models.BooleanField(default=True, help_text='Alertas financieras')
    hr_alerts = models.BooleanField(default=True, help_text='Alertas de RRHH')
    marketing_emails = models.BooleanField(default=False, help_text='Emails de marketing')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferencias: {self.user.username}"


class Notification(TenantAwareModel):
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('push', 'Push'),
        ('sms', 'SMS'),
        ('in_app', 'En aplicación'),
        ('whatsapp', 'WhatsApp'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('scheduled', 'Programado'),
        ('pending', 'Pendiente'),
        ('queued', 'En cola'),
        ('sent', 'Enviado'),
        ('delivered', 'Entregado'),
        ('read', 'Leído'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    customer = models.ForeignKey('crm.Customer', on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    title = models.CharField(max_length=255)
    message = models.TextField()
    html_message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text='Fecha y hora programada para enviar')
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, help_text='Mensaje de error si falló el envío')
    metadata = models.JSONField(default=dict, blank=True, help_text='Datos adicionales')
    related_type = models.CharField(max_length=100, blank=True, help_text='Tipo de modelo relacionado (ej: order, invoice)')
    related_id = models.IntegerField(blank=True, null=True, help_text='ID del modelo relacionado')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        recipient = self.user.username if self.user else self.customer.name if self.customer else self.employee.full_name if self.employee else 'Sin destinatario'
        return f"Notificación: {self.title} - {recipient} ({self.channel})"


class NotificationLog(TenantAwareModel):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20, choices=Notification.STATUS_CHOICES)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Log: {self.notification.title} - {self.status}"


auditlog.register(NotificationTemplate)
auditlog.register(NotificationPreference)
auditlog.register(Notification)
auditlog.register(NotificationLog)

