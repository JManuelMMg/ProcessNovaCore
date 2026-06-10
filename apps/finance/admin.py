from django.contrib import admin
from .models import (
    Account, JournalEntry, TaxConfiguration, Budget, BudgetItem,
    Invoice, InvoiceItem, Income, Expense, Payment
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class BudgetItemInline(admin.TabularInline):
    model = BudgetItem
    extra = 0


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'currency', 'balance', 'is_active', 'organization')
    list_filter = ('organization', 'type', 'currency', 'is_active')
    search_fields = ('name', 'bank_name', 'account_number')


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('account', 'date', 'debit', 'credit', 'reference', 'organization')
    list_filter = ('organization', 'date', 'account')
    search_fields = ('description', 'reference')


@admin.register(TaxConfiguration)
class TaxConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'rate', 'is_active', 'organization')
    list_filter = ('organization', 'type', 'is_active')
    search_fields = ('name',)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('name', 'period_start', 'period_end', 'total_budget', 'total_spent', 'status', 'organization')
    list_filter = ('organization', 'status', 'period_start', 'period_end')
    search_fields = ('name',)
    inlines = [BudgetItemInline]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'customer', 'total', 'paid_amount', 'balance', 'status', 'cfdi_status', 'date', 'organization')
    list_filter = ('organization', 'status', 'cfdi_status', 'date')
    search_fields = ('number', 'customer__name', 'cfdi_uuid')
    inlines = [InvoiceItemInline]


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('amount', 'type', 'date', 'customer', 'invoice', 'account', 'organization')
    list_filter = ('organization', 'type', 'date')
    search_fields = ('description', 'customer__name', 'reference')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('amount', 'category', 'date', 'supplier', 'account', 'is_recurring', 'organization')
    list_filter = ('organization', 'category', 'date', 'is_recurring')
    search_fields = ('description', 'reference')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'method', 'date', 'account', 'organization')
    list_filter = ('organization', 'method', 'date')
    search_fields = ('invoice__number', 'notes', 'reference')

