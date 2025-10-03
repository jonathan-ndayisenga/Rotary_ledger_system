# ledger/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncMonth, TruncYear
import json
from decimal import Decimal
from .models import PaymentIn, PaymentOut, Account, Member
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import JsonResponse
from .forms import MemberForm, MemberSearchForm


# JSON Encoder for Decimals
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# Dashboard
@login_required
def dashboard(request):
    today = timezone.now().date()
    one_year_ago = today - timedelta(days=365)
    five_years_ago = today - timedelta(days=5 * 365)

    view_type = request.GET.get('view', 'months')

    if view_type == 'years':
        yearly_data = PaymentIn.objects.filter(
            payment_date__gte=five_years_ago
        ).annotate(
            year=TruncYear('payment_date')
        ).values('year').annotate(
            total=Sum('amount')
        ).order_by('year')

        chart_labels = [data['year'].strftime('%Y') for data in yearly_data]
        chart_data = [float(data['total'] or 0) for data in yearly_data]
        chart_title = 'Yearly Revenue'

    else:
        monthly_data = PaymentIn.objects.filter(
            payment_date__gte=one_year_ago
        ).annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')

        chart_labels, chart_data = [], []
        for i in range(12):
            month_date = one_year_ago + timedelta(days=30 * i)
            month_str = month_date.strftime('%b %Y')
            chart_labels.append(month_str)

            month_data = next(
                (item for item in monthly_data if item['month'].strftime('%b %Y') == month_str), None
            )
            chart_data.append(float(month_data['total']) if month_data else 0.0)

        chart_title = 'Monthly Revenue (Last 12 Months)'

    compare_data = None
    compare_labels = None
    if 'compare' in request.GET and view_type == 'years':
        ten_years_ago = today - timedelta(days=10 * 365)
        comparison_data = PaymentIn.objects.filter(
            payment_date__gte=ten_years_ago,
            payment_date__lt=five_years_ago
        ).annotate(
            year=TruncYear('payment_date')
        ).values('year').annotate(
            total=Sum('amount')
        ).order_by('year')

        compare_labels = [data['year'].strftime('%Y') for data in comparison_data]
        compare_data = [float(data['total'] or 0) for data in comparison_data]

    accounts = Account.objects.filter(is_active=True)
    total_balance = sum(account.balance for account in accounts)

    avg_monthly = sum(chart_data) / len(chart_data) if chart_data else 0

    context = {
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'chart_title': chart_title,
        'view_type': view_type,
        'compare_data': json.dumps(compare_data) if compare_data else 'null',
        'compare_labels': json.dumps(compare_labels) if compare_labels else 'null',
        'total_balance': total_balance,
        'accounts': accounts,
        'avg_monthly': avg_monthly,
        'current_month_revenue': chart_data[-1] if chart_data else 0,
    }
    return render(request, 'ledger/dashboard.html', context)


# Debug view to check user permissions
class UserStatusView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        return JsonResponse({
            'username': user.username,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'role': getattr(user, 'role', 'No role field'),
            'has_perm_add_member': user.has_perm('ledger.add_member'),
        })


# Permission Mixin - Fixed version
class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to allow superusers and staff users with specific roles"""
    
    def test_func(self):
        user = self.request.user
        
        # Superusers always have access
        if user.is_superuser:
            return True
            
        # Check if user is active
        if not user.is_active:
            return False
            
        # If using CustomUser with role field, check specific roles
        if hasattr(user, 'role'):
            return user.role in ['admin', 'treasurer', 'registrar']
            
        # For regular staff users without role field, allow access
        return True
    
    def handle_no_permission(self):
        """Custom message for permission denied"""
        from django.contrib import messages
        messages.error(self.request, "You don't have permission to access this page. Please contact an administrator.")
        from django.shortcuts import redirect
        return redirect('dashboard')


# Member Views
class MemberListView(LoginRequiredMixin, ListView):
    model = Member
    template_name = 'ledger/member_list.html'
    context_object_name = 'members'
    paginate_by = 20

    def get_queryset(self):
        queryset = Member.objects.all().order_by('name')
        name = self.request.GET.get('name')
        rid = self.request.GET.get('rid')
        club = self.request.GET.get('club')
        buddy_group = self.request.GET.get('buddy_group')

        if name:
            queryset = queryset.filter(name__icontains=name)
        if rid:
            queryset = queryset.filter(rid__icontains=rid)
        if club:
            queryset = queryset.filter(club=club)
        if buddy_group:
            queryset = queryset.filter(buddy_group__icontains=buddy_group)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = MemberSearchForm(self.request.GET)
        context['total_members'] = Member.objects.count()
        return context


# TEMPORARY VERSION - Remove StaffRequiredMixin for testing
class MemberCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Member
    form_class = MemberForm
    template_name = 'ledger/member_form.html'
    success_message = "Member '%(name)s' was created successfully."

    def form_valid(self, form):
        with transaction.atomic():
            member = form.save(commit=False)
            member.created_by = self.request.user
            member.save()

            if form.cleaned_data.get('pay_registration_fee'):
                payment = PaymentIn(
                    payer_member=member,
                    payer_name=member.name,
                    contact=member.contact,
                    email=member.email,
                    revenue_type=form.cleaned_data['revenue_type'],
                    amount=form.cleaned_data['amount'],
                    payment_date=form.cleaned_data['payment_date'] or timezone.now().date(),
                    payment_method=form.cleaned_data['payment_method'],
                    account=form.cleaned_data['account'],
                    created_by=self.request.user
                )
                payment.save()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('member_list')


# TEMPORARY VERSION - Remove StaffRequiredMixin for testing  
class MemberUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Member
    form_class = MemberForm
    template_name = 'ledger/member_form.html'
    success_message = "Member '%(name)s' was updated successfully."

    def get_success_url(self):
        return reverse_lazy('member_list')


class MemberDetailView(LoginRequiredMixin, DetailView):
    model = Member
    template_name = 'ledger/member_detail.html'
    context_object_name = 'member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = PaymentIn.objects.filter(payer_member=self.object)
        return context


class MemberDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Member
    template_name = 'ledger/member_confirm_delete.html'
    success_url = reverse_lazy('member_list')
    success_message = "Member was deleted successfully."


# Final versions with permissions (use these after testing):
"""
class MemberCreateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Member
    form_class = MemberForm
    template_name = 'ledger/member_form.html'
    success_message = "Member '%(name)s' was created successfully."

    def form_valid(self, form):
        with transaction.atomic():
            member = form.save(commit=False)
            member.created_by = self.request.user
            member.save()

            if form.cleaned_data.get('pay_registration_fee'):
                payment = PaymentIn(
                    payer_member=member,
                    payer_name=member.name,
                    contact=member.contact,
                    email=member.email,
                    revenue_type=form.cleaned_data['revenue_type'],
                    amount=form.cleaned_data['amount'],
                    payment_date=form.cleaned_data['payment_date'] or timezone.now().date(),
                    payment_method=form.cleaned_data['payment_method'],
                    account=form.cleaned_data['account'],
                    created_by=self.request.user
                )
                payment.save()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('member_list')


class MemberUpdateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Member
    form_class = MemberForm
    template_name = 'ledger/member_form.html'
    success_message = "Member '%(name)s' was updated successfully."

    def get_success_url(self):
        return reverse_lazy('member_list')
"""