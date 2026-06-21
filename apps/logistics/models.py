from django.db import models
from core.models import TenantAwareModel
from apps.crm.models import Customer
from apps.inventory.models import Product, Warehouse
from auditlog.registry import auditlog


class Carrier(TenantAwareModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=13, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    api_key = models.CharField(max_length=255, blank=True, help_text='API key para integración con el transportista')
    api_url = models.URLField(blank=True, help_text='URL de la API del transportista')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Zone(TenantAwareModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    states = models.JSONField(default=list, blank=True, help_text='Lista de estados que cubre esta zona')
    cities = models.JSONField(default=list, blank=True, help_text='Lista de ciudades que cubre esta zona')
    zip_codes = models.JSONField(default=list, blank=True, help_text='Lista de códigos postales que cubre esta zona')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ShippingRate(TenantAwareModel):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE, related_name='rates')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='rates')
    service_type = models.CharField(max_length=100, blank=True, help_text='Tipo de servicio (ej: Económico, Express)')
    min_weight = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Peso mínimo en kg')
    max_weight = models.DecimalField(max_digits=8, decimal_places=2, default=100, help_text='Peso máximo en kg')
    base_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.carrier.name} - {self.zone.name}"


class Vehicle(TenantAwareModel):
    TYPE_CHOICES = [
        ('truck', 'Camión'),
        ('van', 'Camioneta'),
        ('motorcycle', 'Motocicleta'),
        ('bike', 'Bicicleta'),
        ('other', 'Otro'),
    ]

    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('in_use', 'En uso'),
        ('maintenance', 'Mantenimiento'),
        ('out_of_service', 'Fuera de servicio'),
    ]

    name = models.CharField(max_length=255, help_text='Nombre o identificador del vehículo')
    plate = models.CharField(max_length=50, unique=True, help_text='Placa del vehículo')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='truck')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='available')
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text='Capacidad en kilogramos')
    capacity_volume = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text='Capacidad en metros cúbicos')
    model = models.CharField(max_length=255, blank=True)
    year = models.IntegerField(blank=True, null=True)
    driver_name = models.CharField(max_length=255, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)
    last_maintenance_date = models.DateField(blank=True, null=True)
    next_maintenance_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.plate})"


class Route(TenantAwareModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    origin = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='routes_origin')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='routes')
    driver_name = models.CharField(max_length=255, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)
    vehicle_plate = models.CharField(max_length=50, blank=True)
    stops = models.JSONField(default=list, blank=True, help_text='Lista de paradas: [{"address": "...", "lat": 0.0, "lng": 0.0, "order": 0}]')
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Package(TenantAwareModel):
    tracking_number = models.CharField(max_length=100, unique=True)
    weight = models.DecimalField(max_digits=8, decimal_places=2, help_text='Peso en kg')
    length = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text='Largo en cm')
    width = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text='Ancho en cm')
    height = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text='Alto en cm')
    volume = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text='Volumen en cm³')
    content_description = models.TextField(blank=True)
    declared_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    insurance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.tracking_number

    def calculate_volume(self):
        if self.length and self.width and self.height:
            self.volume = self.length * self.width * self.height
            self.save()


class Shipment(TenantAwareModel):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('ready', 'Listo para envío'),
        ('picked_up', 'Recolectado'),
        ('in_transit', 'En tránsito'),
        ('out_for_delivery', 'En ruta de entrega'),
        ('delivered', 'Entregado'),
        ('failed', 'Fallido'),
        ('returned', 'Devuelto'),
        ('cancelled', 'Cancelado'),
    ]

    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='shipments')
    package = models.OneToOneField(Package, on_delete=models.CASCADE, related_name='shipment', null=True, blank=True)
    carrier = models.ForeignKey(Carrier, on_delete=models.SET_NULL, null=True, blank=True, related_name='shipments')
    tracking_number = models.CharField(max_length=100, blank=True, unique=True)
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True, related_name='shipments')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='shipments')
    shipping_address = models.TextField(blank=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_zip_code = models.CharField(max_length=10, blank=True)
    shipping_phone = models.CharField(max_length=20, blank=True)
    recipient_name = models.CharField(max_length=255, blank=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    status_message = models.TextField(blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    delivery_attempts = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Envío {self.tracking_number} - Pedido {self.order.number}"


class ShipmentTracking(TenantAwareModel):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='trackings')
    status = models.CharField(max_length=30, choices=Shipment.STATUS_CHOICES)
    status_message = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    tracked_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.shipment.tracking_number} - {self.status}"


class DeliveryProof(TenantAwareModel):
    shipment = models.OneToOneField(Shipment, on_delete=models.CASCADE, related_name='proof')
    signature = models.ImageField(upload_to='signatures/', blank=True, null=True)
    photo = models.ImageField(upload_to='delivery_proofs/', blank=True, null=True)
    recipient_name = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    delivered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comprobante de entrega: {self.shipment.tracking_number}"


class Order(TenantAwareModel):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmada'),
        ('processing', 'En proceso'),
        ('shipped', 'Enviada'),
        ('delivered', 'Entregada'),
        ('cancelled', 'Cancelada'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    number = models.CharField(max_length=50, unique=True)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_address = models.TextField(blank=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_zip_code = models.CharField(max_length=10, blank=True)
    shipping_phone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Pedido {self.number} - {self.customer.name}"

    def calculate_totals(self):
        self.subtotal = sum(item.subtotal for item in self.items.all())
        self.tax = sum(item.tax_amount for item in self.items.all())
        self.total = self.subtotal + self.tax + self.shipping_cost - self.discount
        self.save()


class OrderItem(TenantAwareModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=16)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} - Pedido {self.order.number}"

    def save(self, *args, **kwargs):
        self.subtotal = (self.quantity * self.price) - self.discount
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount
        super().save(*args, **kwargs)


auditlog.register(Carrier)
auditlog.register(Zone)
auditlog.register(ShippingRate)
auditlog.register(Vehicle)
auditlog.register(Route)
auditlog.register(Package)
auditlog.register(Shipment)
auditlog.register(ShipmentTracking)
auditlog.register(DeliveryProof)
auditlog.register(Order)
auditlog.register(OrderItem)

