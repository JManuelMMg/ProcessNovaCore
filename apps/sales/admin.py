from django.contrib import admin
from .models import (
    LoyaltyProgram, CustomerLoyalty, Coupon, CommissionPlan, SalesReport,
    Sale, SaleItem, SalesPayment, Refund
)


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


class SalesPaymentInline(admin.TabularInline):
    model = SalesPayment
    extra = 0


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_per_peso', 'is_active', 'organization')
    list_filter = ('organization', 'is_active')
    search_fields = ('name',)


@admin.register(CustomerLoyalty)
class CustomerLoyaltyAdmin(admin.ModelAdmin):
    list_display = ('customer', 'program', 'points_balance', 'organization')
    list_filter = ('organization', 'program')
    search_fields = ('customer__name',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'type', 'value', 'status', 'is_active', 'organization')
    list_filter = ('organization', 'type', 'status', 'is_active')
    search_fields = ('code', 'name')


@admin.register(CommissionPlan)
class CommissionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'percentage', 'is_active', 'organization')
    list_filter = ('organization', 'type', 'is_active')
    search_fields = ('name',)


@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'period', 'start_date', 'end_date', 'total_sales', 'total_orders', 'organization')
    list_filter = ('organization', 'period', 'start_date', 'end_date')
    search_fields = ('name',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'customer', 'type', 'status', 'subtotal', 'discount', 
        'coupon_discount', 'total', 'created_at', 'organization'
    )
    search_fields = ('number', 'customer__name')
    list_filter = ('status', 'type', 'created_at', 'organization')
    inlines = [SaleItemInline, SalesPaymentInline]


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'subtotal', 'total', 'organization')
    list_filter = ('organization',)


@admin.register(SalesPayment)
class SalesPaymentAdmin(admin.ModelAdmin):
    list_display = ('sale', 'amount', 'method', 'created_at', 'organization')
    list_filter = ('method', 'created_at', 'organization')


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('sale', 'amount', 'refund_method', 'created_by', 'created_at', 'organization')
    list_filter = ('organization', 'refund_method', 'created_at')
    search_fields = ('sale__number', 'reason')
