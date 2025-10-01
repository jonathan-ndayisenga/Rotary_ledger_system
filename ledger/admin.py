from django.contrib import admin

# ledger/admin.py
from django.contrib import admin
from .models import *

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'rid', 'email', 'club', 'created_at']
    list_filter = ['club', 'created_at']
    search_fields = ['name', 'rid', 'email']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'supplier_id', 'contact', 'created_at']
    search_fields = ['name', 'supplier_id']

@admin.register(RevenueType)
class RevenueTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'amount_default', 'is_active']

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'account_type', 'balance', 'is_active']

@admin.register(PaymentIn)
class PaymentInAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'payer_name', 'amount', 'payment_date', 'payment_method']
    list_filter = ['payment_date', 'payment_method', 'revenue_type']
    search_fields = ['payer_name', 'receipt_number']

@admin.register(PaymentOut)
class PaymentOutAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'payee_name', 'amount', 'payment_date', 'payment_method']
    list_filter = ['payment_date', 'payment_method']
    search_fields = ['payee_name', 'receipt_number']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'object_type', 'timestamp']
    list_filter = ['action', 'object_type', 'timestamp']
    readonly_fields = ['user', 'action', 'object_type', 'object_id', 'description', 'timestamp']
