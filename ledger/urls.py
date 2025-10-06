# ledger/urls.py
from django.urls import path
from . import views
from .views import (
    MemberListView, MemberCreateView, MemberUpdateView, 
    MemberDetailView, MemberDeleteView, SupplierListView, SupplierCreateView, SupplierUpdateView,
    SupplierDetailView, SupplierDeleteView, PaymentInListView, PaymentInCreateView, 
    PaymentInDetailView, PaymentInDeleteView, PaymentReceiptView
)

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    #memebers urls
    path('members/', MemberListView.as_view(), name='member_list'),
    path('members/create/', MemberCreateView.as_view(), name='member_create'),
    path('members/<int:pk>/', MemberDetailView.as_view(), name='member_detail'),
    path('members/<int:pk>/edit/', MemberUpdateView.as_view(), name='member_update'),
    path('members/<int:pk>/delete/', MemberDeleteView.as_view(), name='member_delete'),

    # Supplier URLs
    path('suppliers/', SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/', SupplierDetailView.as_view(), name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', SupplierUpdateView.as_view(), name='supplier_update'),
    path('suppliers/<int:pk>/delete/', SupplierDeleteView.as_view(), name='supplier_delete'),

    # Payment URLs
    path('payments/', PaymentInListView.as_view(), name='payment_in_list'),
    path('payments/create/', PaymentInCreateView.as_view(), name='payment_in_create'),
    path('payments/<int:pk>/', PaymentInDetailView.as_view(), name='payment_in_detail'),
    path('payments/<int:pk>/delete/', PaymentInDeleteView.as_view(), name='payment_in_delete'),
    path('payments/<int:pk>/receipt/', PaymentReceiptView.as_view(), name='payment_receipt'),
]

