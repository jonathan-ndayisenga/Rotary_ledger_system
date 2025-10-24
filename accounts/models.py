from django.db import models
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('treasurer', 'Treasurer'),
        ('registrar', 'Registrar'),
        ('viewer', 'Viewer'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    phone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    class Meta:
        permissions = [
            ("can_view_reports", "Can view financial reports"),
            ("can_manage_members", "Can manage members"),
            ("can_manage_suppliers", "Can manage suppliers"),
            ("can_record_payments", "Can record payments"),
            ("can_manage_users", "Can manage users"),
        ]


