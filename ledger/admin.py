# ledger/admin.py
from django.contrib import admin
from .models import *

# ExpenseType Admin
@admin.register(ExpenseType)
class ExpenseTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']

# Member Admin
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'rid', 'email', 'club', 'created_at']
    list_filter = ['club', 'created_at']
    search_fields = ['name', 'rid', 'email']

# Supplier Admin
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'supplier_id', 'contact', 'created_at']
    search_fields = ['name', 'supplier_id']

# RevenueType Admin
@admin.register(RevenueType)
class RevenueTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'amount_default', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']

# Account Admin
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'account_type', 'balance', 'is_active', 'bank_name']
    list_filter = ['account_type', 'is_active']
    search_fields = ['name']

# Payment In Admin
@admin.register(PaymentIn)
class PaymentInAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'payer_name', 'amount', 'payment_date', 'payment_method', 'account']
    list_filter = ['payment_date', 'payment_method', 'revenue_type', 'account']
    search_fields = ['payer_name', 'receipt_number', 'payer_member__name']

# Payment Out Admin
@admin.register(PaymentOut)
class PaymentOutAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'payee_name', 'amount', 'payment_date', 'payment_method', 'account']
    list_filter = ['payment_date', 'payment_method', 'account', 'payee_supplier']
    search_fields = ['payee_name', 'receipt_number', 'payee_supplier__name']

# Audit Log Admin
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'object_type', 'timestamp']
    list_filter = ['action', 'object_type', 'timestamp']
    readonly_fields = ['user', 'action', 'object_type', 'object_id', 'description', 'ip_address', 'timestamp']
