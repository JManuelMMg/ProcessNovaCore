from django.db import models
from core.models import TenantAwareModel
from auditlog.registry import auditlog
from django.db.models import Sum, Count


class Segment(TenantAwareModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    criteria = models.JSONField(blank=True, null=True, help_text="Criterios para segmentación automática")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Lead(TenantAwareModel):
    STATUS_CHOICES = [
        ('new', 'Nuevo'),
        ('contacted', 'Contactado'),
        ('qualified', 'Calificado'),
        ('proposal', 'Propuesta'),
        ('won', 'Ganado'),
        ('lost', 'Perdido'),
    ]
    
    SOURCE_CHOICES = [
        ('website', 'Sitio web'),
        ('referral', 'Referencia'),
        ('social', 'Redes sociales'),
        ('ad', 'Publicidad'),
        ('event', 'Evento'),
        ('other', 'Otro'),
    ]

    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='other')
    score = models.IntegerField(default=0, help_text="Puntuación del lead (0-100)")
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_leads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Customer(TenantAwareModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    rfc = models.CharField(max_length=13, blank=True)
    address = models.TextField(blank=True)
    segment = models.ForeignKey(Segment, on_delete=models.SET_NULL, null=True, blank=True, related_name='customers')
    lead = models.OneToOneField(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer')
    lifetime_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    last_purchase_date = models.DateField(null=True, blank=True)
    score = models.IntegerField(default=50, help_text="Puntuación del cliente (0-100)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    def calculate_lifetime_value(self):
        from apps.sales.models import Sale
        sales = Sale.objects.filter(customer=self, status='paid')
        self.lifetime_value = sales.aggregate(Sum('total'))['total__sum'] or 0
        self.total_orders = sales.count()
        last_sale = sales.order_by('-created_at').first()
        if last_sale:
            self.last_purchase_date = last_sale.created_at.date()
        self.save()


class Opportunity(TenantAwareModel):
    STAGE_CHOICES = [
        ('prospecting', 'Prospectación'),
        ('qualification', 'Calificación'),
        ('needs_analysis', 'Análisis de necesidades'),
        ('proposal', 'Propuesta'),
        ('negotiation', 'Negociación'),
        ('closed_won', 'Cerrado ganado'),
        ('closed_lost', 'Cerrado perdido'),
    ]

    name = models.CharField(max_length=255)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='opportunities')
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='opportunities')
    stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default='prospecting')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    probability = models.IntegerField(default=50, help_text="Probabilidad de cierre (%)")
    expected_close_date = models.DateField(null=True, blank=True)
    actual_close_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_opportunities')
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_opportunities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.customer.name}"
    
    @property
    def weighted_amount(self):
        return self.amount * (self.probability / 100)


class Campaign(TenantAwareModel):
    TYPE_CHOICES = [
        ('email', 'Email'),
        ('social', 'Redes sociales'),
        ('sms', 'SMS'),
        ('event', 'Evento'),
        ('other', 'Otro'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('active', 'Activa'),
        ('paused', 'Pausada'),
        ('completed', 'Completada'),
    ]

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    description = models.TextField(blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    target_audience = models.ManyToManyField(Segment, blank=True, related_name='campaigns')
    leads_generated = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    @property
    def roi(self):
        if self.budget > 0:
            return ((self.revenue - self.budget) / self.budget) * 100
        return 0


class Interaction(TenantAwareModel):
    INTERACTION_TYPE_CHOICES = [
        ('call', 'Llamada'),
        ('email', 'Correo electrónico'),
        ('meeting', 'Reunión'),
        ('chat', 'Chat'),
        ('other', 'Otro'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='interactions')
    type = models.CharField(max_length=20, choices=INTERACTION_TYPE_CHOICES)
    notes = models.TextField()
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='interactions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.customer:
            return f"{self.customer.name} - {self.type} ({self.created_at.date()})"
        elif self.lead:
            return f"{self.lead.name} - {self.type} ({self.created_at.date()})"
        return f"{self.type} ({self.created_at.date()})"


auditlog.register(Segment)
auditlog.register(Lead)
auditlog.register(Customer)
auditlog.register(Opportunity)
auditlog.register(Campaign)
auditlog.register(Interaction)

