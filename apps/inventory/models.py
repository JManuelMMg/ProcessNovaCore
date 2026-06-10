import random
import string
from django.db import models
from core.models import TenantAwareModel
from auditlog.registry import auditlog


class Warehouse(TenantAwareModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    manager = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_warehouses')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'organization']

    def __str__(self):
        return self.name


class Location(TenantAwareModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='locations')
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['warehouse', 'code']

    def __str__(self):
        return f"{self.warehouse.name} - {self.code}"


class Category(TenantAwareModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['name', 'organization']

    def __str__(self):
        return self.name


class Product(TenantAwareModel):
    TYPE_CHOICES = [
        ('product', 'Producto físico'),
        ('service', 'Servicio'),
        ('digital', 'Producto digital'),
    ]

    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True, null=True)
    barcode = models.CharField(max_length=255, blank=True, null=True, help_text='Código de barras (EAN-13, UPC, etc.)')
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='product')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text='Peso en kg')
    dimensions = models.CharField(max_length=100, blank=True, help_text='Alto x Ancho x Profundo (cm)')
    is_active = models.BooleanField(default=True)
    is_taxable = models.BooleanField(default=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=16, help_text='Tasa de impuesto (%)')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            ['organization', 'sku'],
            ['organization', 'barcode'],
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def generate_unique_sku(self):
        """Genera un SKU único para la organización"""
        while True:
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            sku = f"PN-{random_part}"
            if not Product.objects.filter(
                organization=self.organization,
                sku=sku
            ).exists():
                return sku

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self.generate_unique_sku()
        super().save(*args, **kwargs)

    def total_stock(self):
        return self.stocks.aggregate(total=models.Sum('quantity'))['total'] or 0

    def stock_at(self, warehouse=None, branch=None):
        if warehouse:
            return self.stocks.filter(location__warehouse=warehouse).aggregate(total=models.Sum('quantity'))['total'] or 0
        if branch:
            return self.stocks.filter(branch=branch).aggregate(total=models.Sum('quantity'))['total'] or 0
        return self.total_stock()


class Stock(TenantAwareModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks')
    branch = models.ForeignKey(
        'users.Branch', on_delete=models.CASCADE, related_name='stocks',
        null=True, blank=True
    )
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='stocks')
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0)
    available_quantity = models.IntegerField(default=0)
    min_quantity = models.IntegerField(default=5, help_text='Stock mínimo para alertas')
    max_quantity = models.IntegerField(default=100, help_text='Stock máximo deseado')
    reorder_point = models.IntegerField(default=10, help_text='Punto de reorden')
    last_restocked = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'branch', 'location', 'organization']

    def __str__(self):
        loc = self.location.code if self.location else self.branch.name if self.branch else 'General'
        return f"{self.product.name} - {loc}: {self.quantity}"

    def save(self, *args, **kwargs):
        self.available_quantity = self.quantity - self.reserved_quantity
        super().save(*args, **kwargs)


class Batch(TenantAwareModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100)
    quantity = models.IntegerField()
    expiry_date = models.DateField(null=True, blank=True)
    manufacture_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['product', 'batch_number', 'organization']
        ordering = ['-expiry_date']

    def __str__(self):
        return f"{self.product.name} - Lote {self.batch_number}"


class StockMovement(TenantAwareModel):
    MOVEMENT_TYPE_CHOICES = [
        ('in', 'Entrada'),
        ('out', 'Salida'),
        ('adjustment', 'Ajuste'),
        ('transfer', 'Transferencia'),
        ('return', 'Devolución'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='movements')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.IntegerField()
    quantity_before = models.IntegerField(blank=True, null=True)
    quantity_after = models.IntegerField(blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='stock_movements')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} - {self.product.name}: {self.quantity}"


class Supplier(TenantAwareModel):
    name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True)
    rfc = models.CharField(max_length=13, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    payment_terms = models.CharField(max_length=255, blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SupplierProduct(TenantAwareModel):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='suppliers')
    supplier_sku = models.CharField(max_length=100, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2)
    lead_time_days = models.IntegerField(default=7, help_text='Días de entrega')
    is_preferred = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['supplier', 'product', 'organization']

    def __str__(self):
        return f"{self.supplier.name} - {self.product.name}"


class PurchaseOrder(TenantAwareModel):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('sent', 'Enviado'),
        ('partial', 'Parcialmente recibido'),
        ('received', 'Recibido'),
        ('cancelled', 'Cancelado'),
    ]

    number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    branch = models.ForeignKey('users.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    date = models.DateField()
    expected_delivery = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='purchase_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OC {self.number} - {self.supplier.name}"

    def calculate_totals(self):
        self.subtotal = sum(item.total for item in self.items.all())
        self.tax = sum(item.tax_amount for item in self.items.all())
        self.total = self.subtotal + self.tax - self.discount
        self.save()


class PurchaseOrderItem(TenantAwareModel):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchase_order_items')
    supplier_product = models.ForeignKey(SupplierProduct, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=16)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount
        super().save(*args, **kwargs)


auditlog.register(Warehouse)
auditlog.register(Location)
auditlog.register(Category)
auditlog.register(Product)
auditlog.register(Stock)
auditlog.register(Batch)
auditlog.register(StockMovement)
auditlog.register(Supplier)
auditlog.register(SupplierProduct)
auditlog.register(PurchaseOrder)
auditlog.register(PurchaseOrderItem)
