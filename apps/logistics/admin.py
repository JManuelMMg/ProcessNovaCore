from django.contrib import admin
from .models import (
    Carrier, Zone, ShippingRate, Route, Package, Shipment, ShipmentTracking, DeliveryProof,
    Order, OrderItem
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class ShipmentTrackingInline(admin.TabularInline):
    model = ShipmentTracking
    extra = 0


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'email', 'phone', 'is_active', 'organization')
    list_filter = ('organization', 'is_active')
    search_fields = ('name', 'code', 'company_name')


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'organization')
    list_filter = ('organization',)
    search_fields = ('name', 'code')


@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ('carrier', 'zone', 'service_type', 'base_cost', 'cost_per_kg', 'is_active', 'organization')
    list_filter = ('organization', 'carrier', 'zone', 'is_active')
    search_fields = ('service_type',)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'origin', 'driver_name', 'is_active', 'organization')
    list_filter = ('organization', 'is_active')
    search_fields = ('name', 'code')


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('tracking_number', 'weight', 'length', 'width', 'height', 'organization')
    list_filter = ('organization',)
    search_fields = ('tracking_number', 'content_description')


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        'tracking_number', 'order', 'package', 'carrier', 'status', 
        'shipping_cost', 'estimated_delivery', 'organization'
    )
    list_filter = ('organization', 'status', 'carrier', 'estimated_delivery')
    search_fields = ('tracking_number', 'order__number', 'recipient_name')
    inlines = [ShipmentTrackingInline]


@admin.register(DeliveryProof)
class DeliveryProofAdmin(admin.ModelAdmin):
    list_display = ('shipment', 'recipient_name', 'delivered_at', 'organization')
    list_filter = ('organization', 'delivered_at')
    search_fields = ('recipient_name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'customer', 'subtotal', 'shipping_cost', 'discount', 
        'total', 'status', 'date', 'organization'
    )
    list_filter = ('organization', 'status', 'date')
    search_fields = ('number', 'customer__name')
    inlines = [OrderItemInline]

