# ledger/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models.functions import TruncMonth, TruncYear
import json
from decimal import Decimal
from .models import PaymentIn, PaymentOut, Account
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.utils import timezone
from .forms import MemberForm, MemberSearchForm
from .models import Member, PaymentIn


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

@login_required
def dashboard(request):
    # Calculate date ranges
    today = timezone.now().date()
    one_year_ago = today - timedelta(days=365)
    five_years_ago = today - timedelta(days=5*365)
    
    # Get view type from request (months or years)
    view_type = request.GET.get('view', 'months')  # Default to months view
    
    # Prepare chart data based on view type
    if view_type == 'years':
        # Yearly data for last 5 years
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
        # Monthly data for last 12 months
        monthly_data = PaymentIn.objects.filter(
            payment_date__gte=one_year_ago
        ).annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        # Create all months for the last year even if no data
        chart_labels = []
        chart_data = []
        
        for i in range(12):
            month_date = one_year_ago + timedelta(days=30*i)
            month_str = month_date.strftime('%b %Y')
            chart_labels.append(month_str)
            
            # Find data for this month
            month_data = next((item for item in monthly_data if item['month'].strftime('%b %Y') == month_str), None)
            chart_data.append(float(month_data['total']) if month_data else 0.0)
        
        chart_title = 'Monthly Revenue (Last 12 Months)'
    
    # Get comparison data if requested
    compare_data = None
    compare_labels = None
    if 'compare' in request.GET and view_type == 'years':
        # Add comparison line for previous period
        ten_years_ago = today - timedelta(days=10*365)
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
    
    # Account balances for sidebar info
    accounts = Account.objects.filter(is_active=True)
    total_balance = sum(account.balance for account in accounts)
    
    # Calculate average monthly revenue
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




class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in ['admin', 'treasurer', 'registrar']

class MemberListView(LoginRequiredMixin, ListView):
    model = Member
    template_name = 'ledger/member_list.html'
    context_object_name = 'members'
    paginate_by = 20

    def get_queryset(self):
        queryset = Member.objects.all().order_by('name')
        
        # Apply filters from search form
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

class MemberCreateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Member
    form_class = MemberForm
    template_name = 'ledger/member_form.html'
    success_message = "Member '%(name)s' was created successfully."
    
    def form_valid(self, form):
        with transaction.atomic():
            # Save the member first
            member = form.save(commit=False)
            member.created_by = self.request.user
            member.save()
            
            # Process payment if registration fee is paid
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
    
    def get_initial(self):
        initial = super().get_initial()
        # Check if member has paid registration fee
        has_payment = PaymentIn.objects.filter(payer_member=self.object).exists()
        initial['pay_registration_fee'] = has_payment
        return initial
    
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

class MemberDeleteView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Member
    template_name = 'ledger/member_confirm_delete.html'
    success_url = reverse_lazy('member_list')
    success_message = "Member was deleted successfully."
    
    def test_func(self):
        # Only admins can delete members
        return super().test_func() and self.request.user.role == 'admin'