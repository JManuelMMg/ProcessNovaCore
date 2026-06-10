from django.db import models
from core.models import TenantAwareModel
from auditlog.registry import auditlog


class Conversation(TenantAwareModel):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='ai_conversations')
    title = models.CharField(max_length=255, blank=True, default='Nueva conversación')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.title[:30]}"


class Message(TenantAwareModel):
    ROLE_CHOICES = [
        ('user', 'Usuario'),
        ('assistant', 'Asistente'),
        ('tool', 'Herramienta'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    tool_call_id = models.CharField(max_length=100, blank=True, null=True)
    tool_name = models.CharField(max_length=100, blank=True, null=True)
    tool_result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.conversation.id} - {self.role}"


class Forecast(TenantAwareModel):
    TYPE_CHOICES = [
        ('sales', 'Ventas'),
        ('inventory', 'Inventario'),
        ('demand', 'Demanda'),
        ('finance', 'Finanzas'),
    ]

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pronóstico {self.type} - {self.period_start} a {self.period_end}"


class Anomaly(TenantAwareModel):
    TYPE_CHOICES = [
        ('sales_spike', 'Pico de ventas'),
        ('stock_shortage', 'Falta de stock'),
        ('payment_delay', 'Retraso de pago'),
        ('expense_anomaly', 'Anomalía en gastos'),
    ]

    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    description = models.TextField()
    related_data = models.JSONField(null=True, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Anomalía: {self.type} - {self.detected_at.date()}"


class Recommendation(TenantAwareModel):
    CATEGORY_CHOICES = [
        ('inventory', 'Inventario'),
        ('pricing', 'Precios'),
        ('marketing', 'Marketing'),
        ('operations', 'Operaciones'),
        ('finance', 'Finanzas'),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=[('low', 'Baja'), ('medium', 'Media'), ('high', 'Alta')], default='medium')
    action_taken = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recomendación: {self.title} - {self.priority}"


auditlog.register(Conversation)
auditlog.register(Message)
auditlog.register(Forecast)
auditlog.register(Anomaly)
auditlog.register(Recommendation)

