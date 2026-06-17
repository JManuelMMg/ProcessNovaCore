from django.db import models
from core.models import TenantAwareModel
from auditlog.registry import auditlog
from apps.inventory.models import Product
from apps.crm.models import Customer
from apps.users.models import User
from django.db.models import Sum


class LoyaltyProgram(TenantAwareModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    points_per_peso = models.DecimalField(max_digits=10, decimal_places=2, default=1, help_text='Puntos ganados por cada peso gastado')
    points_expiration_days = models.IntegerField(default=365, help_text='Días para que los puntos expiren (0 = no expiran)')
    redemption_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.01, help_text='Valor en pesos de cada punto al canjear')
    min_points_to_redeem = models.IntegerField(default=100, help_text='Puntos mínimos necesarios para canjear')
    is_active = models.BooleanField(default=True)
    starts_at = models.DateField(null=True, blank=True)
    ends_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class CustomerLoyalty(TenantAwareModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loyalty')
    program = models.ForeignKey(LoyaltyProgram, on_delete=models.CASCADE, related_name='customers')
    points_balance = models.IntegerField(default=0)
    total_points_earned = models.IntegerField(default=0)
    total_points_redeemed = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['customer', 'program', 'organization']

    def __str__(self):
        return f"{self.customer.name} - {self.program.name}"


class Coupon(TenantAwareModel):
    TYPE_CHOICES = [
        ('percentage', 'Porcentaje'),
        ('fixed', 'Monto fijo'),
        ('free_shipping', 'Envío gratis'),
        ('free_product', 'Producto gratis'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('active', 'Activo'),
        ('expired', 'Expirado'),
        ('inactive', 'Inactivo'),
    ]

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='percentage')
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Valor del descuento (porcentaje o monto)')
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Valor mínimo del pedido para aplicar')
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Descuento máximo permitido')
    usage_limit = models.IntegerField(default=0, help_text='Límite de usos total (0 = ilimitado)')
    usage_per_customer = models.IntegerField(default=0, help_text='Límite de usos por cliente (0 = ilimitado)')
    times_used = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    applicable_products = models.ManyToManyField(Product, blank=True, related_name='coupons')
    applicable_categories = models.ManyToManyField('inventory.Category', blank=True, related_name='coupons')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class CommissionPlan(TenantAwareModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=[
        ('percentage', 'Porcentaje de ventas'),
        ('fixed_per_sale', 'Monto fijo por venta'),
        ('tiered', 'Escalonado'),
    ], default='percentage')
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5, help_text='Porcentaje de comisión')
    fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Monto fijo por venta')
    min_sale_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Venta mínima para aplicar comisión')
    tiers = models.JSONField(default=list, blank=True, help_text='Niveles escalonados: [{"min": 0, "percentage": 5}, ...]')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SalesReport(TenantAwareModel):
    PERIOD_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('yearly', 'Anual'),
        ('custom', 'Personalizado'),
    ]

    name = models.CharField(max_length=255)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='monthly')
    start_date = models.DateField()
    end_date = models.DateField()
    total_sales = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_taxes = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_discounts = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_refunds = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    top_products = models.JSONField(default=list, blank=True)
    top_customers = models.JSONField(default=list, blank=True)
    sales_by_category = models.JSONField(default=dict, blank=True)
    sales_by_branch = models.JSONField(default=dict, blank=True)
    sales_by_salesperson = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales_reports')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"


class Sale(TenantAwareModel):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('pending', 'Pendiente de pago'),
        ('partially_paid', 'Parcialmente pagado'),
        ('paid', 'Pagado'),
        ('refunded', 'Reembolsado'),
        ('partially_refunded', 'Parcialmente reembolsado'),
        ('cancelled', 'Cancelado'),
    ]

    SALE_TYPE_CHOICES = [
        ('pos', 'Punto de venta'),
        ('online', 'Venta online'),
        ('phone', 'Venta telefónica'),
        ('wholesale', 'Mayoreo'),
    ]

    number = models.CharField(max_length=50, unique=True, blank=True)
    branch = models.ForeignKey('users.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales')
    salesperson = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_as_salesperson')
    commission_plan = models.ForeignKey(CommissionPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    type = models.CharField(max_length=20, choices=SALE_TYPE_CHOICES, default='pos')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    coupon_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loyalty_points_earned = models.IntegerField(default=0)
    loyalty_points_redeemed = models.IntegerField(default=0)
    loyalty_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Venta {self.number or '#' + str(self.id)}"

    def save(self, *args, **kwargs):
        from django.db import transaction
        from django.utils import timezone as tz
        
        # Obtener estado anterior si es una actualización
        old_status = None
        if self.pk:
            old_sale = Sale.objects.filter(pk=self.pk).first()
            if old_sale:
                old_status = old_sale.status
        
        # Lógica para generar número único
        if self.pk is None and not self.number:
            with transaction.atomic():
                super().save(*args, **kwargs)
                year = tz.now().year
                self.number = f'VEN-{year}-{str(self.pk).zfill(6)}'
                Sale.objects.filter(pk=self.pk).update(number=self.number)
        else:
            super().save(*args, **kwargs)
        
        # Si la venta pasa a estado PAGADA y tiene cliente, crear interacción CRM y actualizar cliente
        if self.status == 'paid' and old_status != 'paid' and self.customer:
            from apps.crm.models import Interaction
            
            # 1. Crear interacción en CRM
            interaction = Interaction.objects.create(
                organization=self.organization,
                customer=self.customer,
                type='other',
                notes=f"Venta completada: {self.number} - Total: ${self.total:.2f}",
                created_by=self.created_by
            )
            
            # 2. Actualizar datos del cliente (lifetime value, órdenes, última compra)
            self.customer.calculate_lifetime_value()

    def calculate_total(self):
        self.subtotal = self.items.aggregate(Sum('subtotal'))['subtotal__sum'] or 0
        self.tax = self.items.aggregate(Sum('tax_amount'))['tax_amount__sum'] or 0
        self.total = self.subtotal + self.tax + self.shipping_cost - self.discount - self.coupon_discount - self.loyalty_discount
        self.save()


class SaleItem(TenantAwareModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sale_items')
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=16)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_returned = models.BooleanField(default=False)
    returned_quantity = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def save(self, *args, **kwargs):
        if self.product:
            if not self.unit_price:
                self.unit_price = self.product.price
            if not self.cost_price:
                self.cost_price = self.product.cost
        from decimal import Decimal
        self.subtotal = (self.unit_price * self.quantity) - self.discount_amount
        self.tax_amount = self.subtotal * (Decimal(str(self.tax_rate)) / Decimal('100'))
        self.total = self.subtotal + self.tax_amount
        super().save(*args, **kwargs)


class SalesPayment(TenantAwareModel):
    PAYMENT_METHODS = [
        ('cash', 'Efectivo'),
        ('card_debit', 'Tarjeta débito'),
        ('card_credit', 'Tarjeta crédito'),
        ('transfer', 'Transferencia'),
        ('spei', 'SPEI'),
        ('check', 'Cheque'),
        ('loyalty_points', 'Puntos de fidelidad'),
        ('credit_note', 'Nota de crédito'),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='cash')
    reference = models.CharField(max_length=255, blank=True, help_text='Número de referencia, autorización, etc.')
    transaction_id = models.CharField(max_length=255, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_sales_payment'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pago {self.id} - {self.amount} ({self.get_method_display()})"


class Refund(TenantAwareModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='refunds')
    reason = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    refund_method = models.CharField(max_length=30, choices=SalesPayment.PAYMENT_METHODS, default='cash')
    reference = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='refunds')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Reembolso {self.id} - {self.sale.number} - {self.amount}"


auditlog.register(LoyaltyProgram)
auditlog.register(CustomerLoyalty)
auditlog.register(Coupon)
auditlog.register(CommissionPlan)
auditlog.register(SalesReport)
auditlog.register(Sale)
auditlog.register(SaleItem)
auditlog.register(SalesPayment)
auditlog.register(Refund)
