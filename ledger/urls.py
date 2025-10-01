# ledger/urls.py
from django.urls import path
from . import views
from .views import (
    MemberListView, MemberCreateView, MemberUpdateView, 
    MemberDetailView, MemberDeleteView
)

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('members/', MemberListView.as_view(), name='member_list'),
    path('members/create/', MemberCreateView.as_view(), name='member_create'),
    path('members/<int:pk>/', MemberDetailView.as_view(), name='member_detail'),
    path('members/<int:pk>/edit/', MemberUpdateView.as_view(), name='member_update'),
    path('members/<int:pk>/delete/', MemberDeleteView.as_view(), name='member_delete'),
]