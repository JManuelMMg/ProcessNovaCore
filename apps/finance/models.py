from django.db import models
from core.models import TenantAwareModel
from apps.crm.models import Customer
from auditlog.registry import auditlog
from django.db.models import Sum


class Account(TenantAwareModel):
    TYPE_CHOICES = [
        ('cash', 'Efectivo'),
        ('bank', 'Banco'),
        ('credit_card', 'Tarjeta de crédito'),
        ('loan', 'Préstamo'),
        ('other', 'Otro'),
    ]
    
    CURRENCY_CHOICES = [
        ('MXN', 'Pesos Mexicanos'),
        ('USD', 'Dólares'),
    ]

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='MXN')
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bank_name = models.CharField(max_length=255, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    def calculate_balance(self):
        from_date = self.created_at.date()
        entries = JournalEntry.objects.filter(account=self, date__gte=from_date)
        total_debit = entries.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = entries.aggregate(Sum('credit'))['credit__sum'] or 0
        self.balance = self.initial_balance + total_debit - total_credit
        self.save()


class JournalEntry(TenantAwareModel):
    TYPE_CHOICES = [
        ('debit', 'Débito'),
        ('credit', 'Crédito'),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='entries')
    date = models.DateField()
    description = models.TextField(blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    reference = models.CharField(max_length=255, blank=True)
    invoice = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')
    expense = models.ForeignKey('Expense', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')
    income = models.ForeignKey('Income', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account.name} - {self.description[:50]}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.account.calculate_balance()


class TaxConfiguration(TenantAwareModel):
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Tasa impositiva (%)")
    type = models.CharField(max_length=20, choices=[('iva', 'IVA'), ('isr', 'ISR'), ('ieps', 'IEPS'), ('other', 'Otro')])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class Budget(TenantAwareModel):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('approved', 'Aprobado'),
        ('active', 'Activo'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ]

    name = models.CharField(max_length=255)
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.period_start} - {self.period_end})"
    
    @property
    def remaining(self):
        return self.total_budget - self.total_spent
    
    @property
    def percentage_spent(self):
        if self.total_budget > 0:
            return (self.total_spent / self.total_budget) * 100
        return 0


class BudgetItem(TenantAwareModel):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='items')
    category = models.CharField(max_length=100)
    allocated = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.budget.name} - {self.category}"
    
    @property
    def remaining(self):
        return self.allocated - self.spent


class Invoice(TenantAwareModel):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('stamped', 'Timbrada'),
        ('sent', 'Enviada'),
        ('paid', 'Pagada'),
        ('overdue', 'Vencida'),
        ('cancelled', 'Cancelada'),
    ]
    CFDI_STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('stamped', 'Timbrada'),
        ('cancelled', 'Cancelada'),
    ]

    sale = models.ForeignKey(
        'sales.Sale', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices'
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    number = models.CharField(max_length=50)
    serie = models.CharField(max_length=10, default='A')
    folio = models.PositiveIntegerField(default=1)
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cfdi_uuid = models.CharField(max_length=36, blank=True, null=True)
    cfdi_status = models.CharField(max_length=20, choices=CFDI_STATUS_CHOICES, default='pending')
    uso_cfdi = models.CharField(max_length=10, default='G03')
    forma_pago = models.CharField(max_length=5, default='01')
    metodo_pago = models.CharField(max_length=5, default='PUE')
    tipo_comprobante = models.CharField(max_length=5, default='I')
    xml_content = models.TextField(blank=True)
    stamped_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['organization', 'number']
        ordering = ['-created_at']

    def __str__(self):
        return f"Factura {self.number} - {self.customer.name}"

    def calculate_totals(self):
        items = self.items.all()
        self.subtotal = sum(i.subtotal for i in items)
        self.tax = sum(i.tax_amount for i in items)
        self.total = self.subtotal + self.tax - self.discount
        self.balance = self.total - self.paid_amount
        self.save()


class InvoiceItem(TenantAwareModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'inventory.Product', on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=16)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    clave_prod_serv = models.CharField(max_length=20, default='01010101')
    clave_unidad = models.CharField(max_length=10, default='H87')

    def save(self, *args, **kwargs):
        self.subtotal = (self.quantity * self.unit_price) - self.discount
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        super().save(*args, **kwargs)


class Income(TenantAwareModel):
    INCOME_TYPE_CHOICES = [
        ('sale', 'Venta'),
        ('service', 'Servicio'),
        ('interest', 'Intereses'),
        ('refund', 'Reembolso'),
        ('other', 'Otro'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='incomes')
    sale = models.ForeignKey('sales.Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='incomes')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='incomes')
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='incomes')
    type = models.CharField(max_length=20, choices=INCOME_TYPE_CHOICES, default='sale')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField()
    reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ingreso: ${self.amount} ({self.date})"


class Expense(TenantAwareModel):
    CATEGORY_CHOICES = [
        ('salaries', 'Salarios'),
        ('rent', 'Renta'),
        ('utilities', 'Servicios'),
        ('supplies', 'Insumos'),
        ('marketing', 'Marketing'),
        ('travel', 'Viajes'),
        ('insurance', 'Seguros'),
        ('other', 'Otro'),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    supplier = models.ForeignKey('inventory.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    date = models.DateField()
    reference = models.CharField(max_length=255, blank=True)
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)
    is_recurring = models.BooleanField(default=False)
    recurrence_interval = models.CharField(max_length=20, choices=[('daily', 'Diario'), ('weekly', 'Semanal'), ('monthly', 'Mensual'), ('yearly', 'Anual')], blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Gasto: ${self.amount} - {self.category} ({self.date})"


class Payment(TenantAwareModel):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Efectivo'),
        ('card', 'Tarjeta'),
        ('transfer', 'Transferencia'),
        ('check', 'Cheque'),
        ('spei', 'SPEI'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago: ${self.amount} - {self.invoice.number} ({self.date})"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.invoice.paid_amount += self.amount
            self.invoice.balance = self.invoice.total - self.invoice.paid_amount
            if self.invoice.balance <= 0:
                self.invoice.status = 'paid'
            elif self.invoice.due_date and self.invoice.due_date < self.date:
                self.invoice.status = 'overdue'
            self.invoice.save()


auditlog.register(Account)
auditlog.register(JournalEntry)
auditlog.register(TaxConfiguration)
auditlog.register(Budget)
auditlog.register(BudgetItem)
auditlog.register(Invoice)
auditlog.register(InvoiceItem)
auditlog.register(Income)
auditlog.register(Expense)
auditlog.register(Payment)
