from django.contrib import admin
from .models import (
    Warehouse, Location, Category, Product, Stock, Batch, StockMovement,
    Supplier, SupplierProduct, PurchaseOrder, PurchaseOrderItem
)


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'city', 'manager', 'is_active', 'organization')
    list_filter = ('organization', 'city', 'is_active')
    search_fields = ('name', 'code')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'code', 'name', 'organization')
    list_filter = ('organization', 'warehouse')
    search_fields = ('code', 'name')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'organization', 'created_at')
    search_fields = ('name',)
    list_filter = ('organization',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'type', 'price', 'is_active', 'organization', 'created_at')
    search_fields = ('name', 'sku', 'barcode')
    list_filter = ('organization', 'category', 'type', 'is_active')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'branch', 'location', 'quantity', 'available_quantity', 'min_quantity', 'organization')
    list_filter = ('organization', 'branch', 'location')
    search_fields = ('product__name', 'product__sku', 'product__barcode')


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('product', 'batch_number', 'quantity', 'expiry_date', 'stock', 'organization')
    list_filter = ('organization', 'expiry_date')
    search_fields = ('product__name', 'batch_number')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'type', 'quantity', 'stock', 'batch', 'created_at', 'organization')
    list_filter = ('organization', 'type', 'created_at')
    search_fields = ('product__name', 'reference')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_name', 'email', 'phone', 'is_active', 'organization')
    list_filter = ('organization', 'is_active')
    search_fields = ('name', 'company_name', 'email', 'phone')


@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'product', 'cost', 'is_preferred', 'is_active', 'organization')
    list_filter = ('organization', 'is_preferred', 'is_active')
    search_fields = ('product__name', 'supplier__name')


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('number', 'supplier', 'status', 'total', 'date', 'organization')
    list_filter = ('organization', 'status', 'date')
    search_fields = ('number', 'supplier__name')
    inlines = [PurchaseOrderItemInline]

