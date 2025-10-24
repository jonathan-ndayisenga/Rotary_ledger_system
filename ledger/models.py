# ledger/models.py
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()

class ExpenseType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Member(models.Model):
    CLUB_CHOICES = [
        ('rotaract', 'Rotaract Club'),
        ('rotary', 'Rotary Club'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    rid = models.CharField(max_length=20, unique=True, verbose_name="RID")
    contact = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    residence = models.CharField(max_length=200)
    club = models.CharField(max_length=50, choices=CLUB_CHOICES, default='rotaract')
    other_club_name = models.CharField(max_length=200, blank=True, null=True)
    buddy_group = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        if self.club == "other" and self.other_club_name:
            return f"{self.name} ({self.rid}) - {self.other_club_name}"
        return f"{self.name} ({self.rid})"
    
    class Meta:
        ordering = ['name']

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    bank_details = models.TextField(blank=True)
    supplier_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class RevenueType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    amount_default = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('cash', 'Cash'),
        ('bank', 'Bank Account'),
        ('mobile', 'Mobile Money'),
    ]
    
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES)
    account_number = models.CharField(max_length=50, blank=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

from decimal import Decimal
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()

class PaymentIn(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('mobile', 'Mobile Money'),
        ('cheque', 'Cheque'),
    ]
    
    payer_member = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True, blank=True)
    payer_name = models.CharField(max_length=200)
    contact = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    revenue_type = models.ForeignKey('RevenueType', on_delete=models.PROTECT)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    account = models.ForeignKey('Account', on_delete=models.PROTECT)
    receipt_number = models.CharField(max_length=20, unique=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
def save(self, *args, **kwargs):
    is_new = self._state.adding
    old = None

    if not is_new:
        try:
            old = PaymentIn.objects.get(pk=self.pk)
        except PaymentIn.DoesNotExist:
            old = None

    # Generate a unique receipt number safely
    if not self.receipt_number:
        base_prefix = f"RC-{self.payment_date.strftime('%Y%m')}-"
        last = (
            PaymentIn.objects
            .filter(receipt_number__startswith=base_prefix)
            .order_by('-id')
            .first()
        )

        last_number = 0
        if last and last.receipt_number:
            try:
                last_number = int(last.receipt_number.split('-')[-1])
            except (IndexError, ValueError):
                last_number = 0

        new_number = last_number + 1

        # Ensure absolute uniqueness (important for SQLite)
        while PaymentIn.objects.filter(receipt_number=f"{base_prefix}{new_number:04d}").exists():
            new_number += 1

        self.receipt_number = f"{base_prefix}{new_number:04d}"

    # --- Balance handling ---
    with transaction.atomic():
        super().save(*args, **kwargs)

        if is_new:
            # New payment — increase balance
            self.account.balance += self.amount
            self.account.save()
        elif old:
            # Update case
            if old.account_id != self.account_id:
                # Account changed
                old.account.balance -= old.amount
                old.account.save()
                self.account.balance += self.amount
                self.account.save()
            else:
                # Same account, maybe amount changed
                diff = self.amount - old.amount
                if diff != 0:
                    self.account.balance += diff
                    self.account.save()


def delete(self, *args, **kwargs):
    with transaction.atomic():
        acct = self.account
        acct.balance -= self.amount
        acct.save()
        return super().delete(*args, **kwargs)


def __str__(self):
    return f"Receipt {self.receipt_number} - {self.payer_name}"


class PaymentOut(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('cheque', 'Cheque'),
    ]
    
    payee_supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True)
    payee_name = models.CharField(max_length=200)
    contact = models.CharField(max_length=15, blank=True)
    reason = models.TextField()
    
    # New fields
    expense_type = models.CharField(max_length=255)
    invoice_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    account = models.ForeignKey('Account', on_delete=models.PROTECT)
    receipt_number = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            last_payment = PaymentOut.objects.order_by('-id').first()
            last_number = int(last_payment.receipt_number.split('-')[-1]) if last_payment else 0
            self.receipt_number = f"PY-{self.payment_date.strftime('%Y%m')}-{last_number + 1:04d}"
        
        super().save(*args, **kwargs)
        self.account.balance -= self.amount
        self.account.save()
    
    def __str__(self):
        return f"Payment {self.receipt_number} - {self.payee_name}"
    

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    object_type = models.CharField(max_length=50)
    object_id = models.IntegerField(null=True, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user} {self.action} {self.object_type} at {self.timestamp}"
    

# class PaymentIn(models.Model):
#     recorded_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='recorded_payments'
#     )