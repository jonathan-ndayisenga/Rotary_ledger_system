# ledger/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncMonth, TruncYear
import json
from decimal import Decimal
from .models import PaymentIn, PaymentOut, Account, Member, Supplier, RevenueType, ExpenseType
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from .forms import PaymentOutForm
from itertools import chain

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
    view_type = request.GET.get('view', 'months')

    accounts = Account.objects.filter(is_active=True)
    total_balance = sum(account.balance for account in accounts)

    chart_labels, chart_data, chart_title = [], [], ""

    if view_type == 'years':
        # Last 5 years
        start_year = today.year - 4
        yearly_data = PaymentIn.objects.filter(
            payment_date__year__gte=start_year
        ).annotate(
            year=TruncYear('payment_date')
        ).values('year').annotate(
            total=Sum('amount')
        ).order_by('year')

        for y in range(start_year, today.year + 1):
            chart_labels.append(str(y))
            data = next((item for item in yearly_data if item['year'].year == y), None)
            chart_data.append(float(data['total'] or 0) if data else 0.0)

        chart_title = 'Yearly Revenue (Last 5 Years)'

        # Optional comparison (previous 5 years)
        compare_data = None
        compare_labels = None
        if 'compare' in request.GET:
            compare_start_year = start_year - 5
            comparison_data = PaymentIn.objects.filter(
                payment_date__year__gte=compare_start_year,
                payment_date__year__lt=start_year
            ).annotate(
                year=TruncYear('payment_date')
            ).values('year').annotate(
                total=Sum('amount')
            ).order_by('year')

            compare_labels = [str(y) for y in range(compare_start_year, start_year)]
            compare_data = []
            for y in range(compare_start_year, start_year):
                data = next((item for item in comparison_data if item['year'].year == y), None)
                compare_data.append(float(data['total'] or 0) if data else 0.0)
    else:
        # Last 12 months
        chart_title = 'Monthly Revenue (Last 12 Months)'
        current_month = today.replace(day=1)
        start_month = current_month - relativedelta(months=11)

        monthly_data = PaymentIn.objects.filter(
            payment_date__gte=start_month
        ).annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')

        for i in range(12):
            month_date = start_month + relativedelta(months=i)
            label = month_date.strftime('%b %Y')
            chart_labels.append(label)
            data = next((item for item in monthly_data if item['month'].year == month_date.year and item['month'].month == month_date.month), None)
            chart_data.append(float(data['total'] or 0) if data else 0.0)

        compare_data = None
        compare_labels = None

    avg_monthly = sum(chart_data) / len(chart_data) if chart_data else 0
    current_month_revenue = chart_data[-1] if chart_data else 0

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
        'current_month_revenue': current_month_revenue,
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

# Permission Mixin
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
        messages.error(self.request, "You don't have permission to access this page. Please contact an administrator.")
        return redirect('dashboard')

# Payment Receipt View
class PaymentReceiptView(LoginRequiredMixin, DetailView):
    model = PaymentIn
    template_name = 'ledger/payments/payment_receipt.html'
    context_object_name = 'payment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context data needed for the receipt
        return context

# Member Views
class MemberListView(LoginRequiredMixin, ListView):
    model = Member
    template_name = 'ledger/members/member_list.html'
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
        from .forms import MemberSearchForm
        context['search_form'] = MemberSearchForm(self.request.GET)
        context['total_members'] = Member.objects.count()
        return context

class MemberCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Member
    template_name = 'ledger/members/member_form.html'
    success_message = "Member '%(name)s' was created successfully."

    def get_form_class(self):
        from .forms import MemberForm
        return MemberForm

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

class MemberUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Member
    template_name = 'ledger/members/member_form.html'
    success_message = "Member '%(name)s' was updated successfully."

    def get_form_class(self):
        from .forms import MemberForm
        return MemberForm

    def get_success_url(self):
        return reverse_lazy('member_list')

class MemberDetailView(LoginRequiredMixin, DetailView):
    model = Member
    template_name = 'ledger/members/member_detail.html'
    context_object_name = 'member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = PaymentIn.objects.filter(payer_member=self.object)
        return context

class MemberDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Member
    template_name = 'ledger/members/member_confirm_delete.html'
    success_url = reverse_lazy('member_list')
    success_message = "Member was deleted successfully."

# Supplier Views
class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'ledger/suppliers/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 20

    def get_queryset(self):
        queryset = Supplier.objects.all().order_by('name')
        
        # Apply filters from search form
        name = self.request.GET.get('name')
        supplier_id = self.request.GET.get('supplier_id')
        contact = self.request.GET.get('contact')
        
        if name:
            queryset = queryset.filter(name__icontains=name)
        if supplier_id:
            queryset = queryset.filter(supplier_id__icontains=supplier_id)
        if contact:
            queryset = queryset.filter(contact__icontains=contact)
            
        return queryset

    def get_context_data(self, **kwargs):
        from .forms import SupplierSearchForm
        context = super().get_context_data(**kwargs)
        context['search_form'] = SupplierSearchForm(self.request.GET)
        context['total_suppliers'] = self.model.objects.count()
        return context

class SupplierCreateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Supplier
    template_name = 'ledger/suppliers/supplier_form.html'
    success_message = "Supplier '%(name)s' was created successfully."
    
    def get_form_class(self):
        from .forms import SupplierForm
        return SupplierForm
    
    def form_valid(self, form):
        supplier = form.save(commit=False)
        supplier.created_by = self.request.user
        supplier.save()
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('supplier_list')

class SupplierUpdateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Supplier
    template_name = 'ledger/suppliers/supplier_form.html'
    success_message = "Supplier '%(name)s' was updated successfully."
    
    def get_form_class(self):
        from .forms import SupplierForm
        return SupplierForm
    
    def get_success_url(self):
        return reverse_lazy('supplier_list')

class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = 'ledger/suppliers/supplier_detail.html'
    context_object_name = 'supplier'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = PaymentOut.objects.filter(payee_supplier=self.object)
        context['total_paid'] = PaymentOut.objects.filter(
            payee_supplier=self.object
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        return context

class SupplierDeleteView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Supplier
    template_name = 'ledger/suppliers/supplier_confirm_delete.html'
    success_url = reverse_lazy('supplier_list')
    success_message = "Supplier was deleted successfully."

# Payment In Views
class PaymentInListView(LoginRequiredMixin, ListView):
    model = PaymentIn
    template_name = 'ledger/payments/payment_in_list.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        queryset = PaymentIn.objects.select_related(
            'payer_member', 'revenue_type', 'account'
        ).order_by('-payment_date', '-created_at')
        
        # Filters
        payer_name = self.request.GET.get('payer_name')
        receipt_number = self.request.GET.get('receipt_number')
        revenue_type = self.request.GET.get('revenue_type')
        payment_date_range = self.request.GET.get('payment_date_range')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if payer_name:
            queryset = queryset.filter(payer_name__icontains=payer_name)
        if receipt_number:
            queryset = queryset.filter(receipt_number__icontains=receipt_number)
        if revenue_type:
            queryset = queryset.filter(revenue_type_id=revenue_type)

        today = timezone.now().date()
        if payment_date_range:
            if payment_date_range == 'today':
                queryset = queryset.filter(payment_date=today)
            elif payment_date_range == 'week':
                start_of_week = today - timedelta(days=today.weekday())
                queryset = queryset.filter(payment_date__gte=start_of_week)
            elif payment_date_range == 'month':
                start_of_month = today.replace(day=1)
                queryset = queryset.filter(payment_date__gte=start_of_month)
            elif payment_date_range == 'year':
                start_of_year = today.replace(month=1, day=1)
                queryset = queryset.filter(payment_date__gte=start_of_year)
            elif payment_date_range == 'custom' and start_date and end_date:
                queryset = queryset.filter(
                    payment_date__gte=start_date,
                    payment_date__lte=end_date
                )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .forms import PaymentInSearchForm

        queryset = self.get_queryset()
        context['search_form'] = PaymentInSearchForm(self.request.GET)

        # Totals
        context['total_amount'] = queryset.aggregate(Sum('amount'))['amount__sum'] or 0
        context['total_count'] = queryset.count()

        # Monthly total
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        month_total = PaymentIn.objects.filter(payment_date__gte=start_of_month).aggregate(Sum('amount'))['amount__sum'] or 0
        context['month_total'] = month_total

        return context

class PaymentInCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = PaymentIn
    template_name = 'ledger/payments/payment_in_form.html'
    success_message = "Payment was recorded successfully."
    
    def get_form_class(self):
        from .forms import PaymentInForm
        return PaymentInForm
    
    def form_valid(self, form):
        payment = form.save(commit=False)
        payment.created_by = self.request.user
        
        # Generate receipt number if not provided
        if not payment.receipt_number:
            payment.receipt_number = self.generate_receipt_number()
        
        payment.save()
        return super().form_valid(form)
    
    def generate_receipt_number(self):
        # Simple receipt number generation
        today = timezone.now().date()
        last_payment = PaymentIn.objects.filter(
            payment_date=today
        ).order_by('-receipt_number').first()
        
        if last_payment and last_payment.receipt_number:
            try:
                last_num = int(last_payment.receipt_number.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
            
        return f"REC-{today.strftime('%Y%m%d')}-{new_num:04d}"
    
    def get_success_url(self):
        return reverse_lazy('payment_in_list')

class PaymentInDetailView(LoginRequiredMixin, DetailView):
    model = PaymentIn
    template_name = 'ledger/payments/payment_in_detail.html'
    context_object_name = 'payment'

class PaymentInUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = PaymentIn
    template_name = 'ledger/payments/payment_in_form.html'
    success_message = "Payment was updated successfully."
    
    def get_form_class(self):
        from .forms import PaymentInForm
        return PaymentInForm
    
    def get_success_url(self):
        return reverse_lazy('payment_in_list')

class PaymentInDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = PaymentIn
    template_name = 'ledger/payments/payment_in_confirm_delete.html'
    success_url = reverse_lazy('payment_in_list')
    success_message = "Payment was deleted successfully."

# Payment Out Views
class PaymentOutListView(LoginRequiredMixin, ListView):
    model = PaymentOut
    template_name = 'ledger/payments/payment_out_list.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        queryset = PaymentOut.objects.select_related(
            'payee_supplier', 'account'
        ).order_by('-payment_date', '-created_at')
        
        # Add filters similar to PaymentInListView
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add totals and other context data
        return context

class PaymentOutCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = PaymentOut
    form_class = PaymentOutForm
    template_name = 'ledger/payments/payment_out_form.html'
    success_message = "Payment out was recorded successfully."

    def test_func(self):
        user = self.request.user
        return user.is_superuser or getattr(user, 'role', '') in ['admin', 'treasurer']

    def form_valid(self, form):
        with transaction.atomic():
            new_supplier_name = form.cleaned_data.get('new_supplier_name')
            if new_supplier_name:
                supplier = Supplier.objects.create(
                    name=new_supplier_name,
                    contact=form.cleaned_data.get('new_supplier_contact', ''),
                    email=form.cleaned_data.get('new_supplier_email', ''),
                    created_by=self.request.user,
                    supplier_id=f"S-{Supplier.objects.count() + 1:04d}"
                )
                form.instance.payee_supplier = supplier
                form.instance.payee_name = supplier.name  # <-- set here
            else:
                # If a supplier is selected
                if form.instance.payee_supplier:
                    form.instance.payee_name = form.instance.payee_supplier.name
                    form.instance.contact = form.instance.payee_supplier.contact

            # If payee_name is still empty, try to get it from the form field
            if not form.instance.payee_name:
                form.instance.payee_name = form.cleaned_data.get('payee_name', 'Unknown')

            form.instance.created_by = self.request.user

            return super().form_valid(form)


    def get_success_url(self):
        return reverse_lazy('payment_out_list')

class PaymentOutDetailView(LoginRequiredMixin, DetailView):
    model = PaymentOut
    template_name = 'ledger/payments/payment_out_detail.html'
    context_object_name = 'payment'

class PaymentOutUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = PaymentOut
    template_name = 'ledger/payments/payment_out_form.html'
    success_message = "Payment out was updated successfully."
    
    def get_form_class(self):
        from .forms import PaymentOutForm
        return PaymentOutForm
    
    def get_success_url(self):
        return reverse_lazy('payment_out_list')

class PaymentOutDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = PaymentOut
    template_name = 'ledger/payments/payment_out_confirm_delete.html'
    success_url = reverse_lazy('payment_out_list')
    success_message = "Payment out was deleted successfully."

# Account Views
class AccountListView(LoginRequiredMixin, ListView):
    model = Account
    template_name = 'ledger/accounts/account_list.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        return Account.objects.filter(is_active=True).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_balance'] = sum(account.balance for account in context['accounts'])
        return context

class AccountCreateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Account
    template_name = 'ledger/accounts/account_form.html'
    success_message = "Account was created successfully."
    
    def get_form_class(self):
        from .forms import AccountForm
        return AccountForm
    
    def get_success_url(self):
        return reverse_lazy('account_list')

class AccountUpdateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Account
    template_name = 'ledger/accounts/account_form.html'
    success_message = "Account was updated successfully."
    
    def get_form_class(self):
        from .forms import AccountForm
        return AccountForm
    
    def get_success_url(self):
        return reverse_lazy('account_list')

class AccountDetailView(LoginRequiredMixin, DetailView):
    model = Account
    template_name = 'ledger/accounts/account_detail.html'
    context_object_name = 'account'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments_in'] = PaymentIn.objects.filter(account=self.object)
        context['payments_out'] = PaymentOut.objects.filter(account=self.object)
        return context


class PaymentInPrintView(View):
    template_name = "ledger/payments/payment_in_receipt.html"

    def get(self, request, pk):
        payment = get_object_or_404(PaymentIn, pk=pk)
        context = {
            "payment": payment,
        }
        return render(request, self.template_name, context)
    

 #payment out receipt view
@login_required 
def payment_out_receipt_view(request, pk):
    payment = get_object_or_404(PaymentOut, pk=pk)
    context = {
        'payment': payment
    }
    return render(request, "ledger/payments/payment_out_receipt.html", context)

# ledger/views.py - Add after other views

class MemberCashbookView(View):
    def get(self, request, pk):
        member = get_object_or_404(Member, pk=pk)

        # Filter payments linked to this member
        payments = PaymentIn.objects.filter(payer_member=member).order_by('payment_date')

        total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0
        payment_count = payments.count()

        payment_history = []
        running_balance = 0
        for p in payments:
            running_balance += p.amount
            payment_history.append({'payment': p, 'running_balance': running_balance})

        context = {
            'member': member,
            'payments': payments,
            'payment_history': payment_history,
            'total_paid': total_paid,
            'payment_count': payment_count,
            'current_balance': running_balance,
            
        }
        return render(request, 'ledger/members/member_cashbook.html', context)

# class MemberPaymentHistoryView(LoginRequiredMixin, ListView):
#     """Alternative view showing just payment history table"""
#     model = PaymentIn
#     template_name = 'ledger/members/member_payment_history.html'
#     context_object_name = 'payments'
#     paginate_by = 20

#     def get_queryset(self):
#         member_id = self.kwargs['pk']
#         queryset = PaymentIn.objects.filter(
#             payer_member_id=member_id
#         ).select_related('revenue_type', 'account').order_by('-payment_date')
        
#         # Apply date filtering
#         start_date = self.request.GET.get('start_date')
#         end_date = self.request.GET.get('end_date')
        
#         if start_date:
#             queryset = queryset.filter(payment_date__gte=start_date)
#         if end_date:
#             queryset = queryset.filter(payment_date__lte=end_date)
            
#         return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member_id = self.kwargs['pk']
        context['member'] = Member.objects.get(pk=member_id)
        
        # Calculate totals
        queryset = self.get_queryset()
        context['total_paid'] = queryset.aggregate(Sum('amount'))['amount__sum'] or 0
        context['payment_count'] = queryset.count()
        
        return context
    

    # cashbook view
@login_required
def cashbook_view(request):
    # Get date range from request, default to current month if not provided
    today = timezone.now().date()
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Set default date range to current month if not provided
    if not start_date:
        start_date = today.replace(day=1)  # First day of current month
    if not end_date:
        end_date = today  # Today
    
    # Convert string dates to date objects if they're strings
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get opening balance (balance before start_date)
    opening_balance = 0
    try:
        # Sum of all accounts' balances at the start of the period
        # Note: This assumes your account balances are current. For a real system, 
        # you'd calculate balance up to the day before start_date
        accounts = Account.objects.filter(is_active=True)
        opening_balance = sum(account.balance for account in accounts)
        
        # Adjust for transactions that haven't been recorded in the period
        # This is a simplified approach - in a real system, you'd track historical balances
        pre_period_payments_in = PaymentIn.objects.filter(payment_date__lt=start_date).aggregate(Sum('amount'))['amount__sum'] or 0
        pre_period_payments_out = PaymentOut.objects.filter(payment_date__lt=start_date).aggregate(Sum('amount'))['amount__sum'] or 0
        opening_balance = pre_period_payments_in - pre_period_payments_out
        
    except Exception as e:
        # If there's any error calculating opening balance, default to 0
        opening_balance = 0
    
    # Get all transactions in the date range, ordered by date
    payments_in = PaymentIn.objects.filter(
        payment_date__range=[start_date, end_date]
    ).select_related('revenue_type', 'account').order_by('payment_date', 'id')
    
    payments_out = PaymentOut.objects.filter(
        payment_date__range=[start_date, end_date]
    ).select_related('account').order_by('payment_date', 'id')
    
    # Merge and sort transactions chronologically
    all_transactions = sorted(
        chain(payments_in, payments_out),
        key=lambda transaction: (transaction.payment_date, getattr(transaction, 'id', 0))
    )
    
    # Calculate running balance
    cashbook_entries = []
    balance = opening_balance
    
    # Add opening balance as first entry
    cashbook_entries.append({
        'date': start_date,
        'type': 'Opening Balance',
        'description': 'Opening Balance',
        'reference': '-',
        'receipts': None,
        'payments': None,
        'balance': balance,
        'is_opening': True
    })
    
    for transaction in all_transactions:
        if isinstance(transaction, PaymentIn):
            balance += transaction.amount
            entry_type = 'Receipt'
            description = f"{transaction.payer_name} - {transaction.revenue_type.name}"
            reference = transaction.receipt_number
        else:
            balance -= transaction.amount
            entry_type = 'Payment'
            description = f"{transaction.payee_name} - {transaction.reason}"
            reference = transaction.receipt_number
        
        cashbook_entries.append({
            'date': transaction.payment_date,
            'type': entry_type,
            'description': description,
            'reference': reference,
            'receipts': transaction.amount if isinstance(transaction, PaymentIn) else None,
            'payments': transaction.amount if isinstance(transaction, PaymentOut) else None,
            'balance': balance,
            'transaction': transaction,
            'account': transaction.account  if hasattr(transaction, 'account') else None,
            'is_opening': False
        })
    
    # Calculate totals
    total_receipts = sum(entry['receipts'] or 0 for entry in cashbook_entries)
    total_payments = sum(entry['payments'] or 0 for entry in cashbook_entries)
    net_movement = total_receipts - total_payments
    closing_balance = opening_balance + net_movement
    
    context = {
        'cashbook_entries': cashbook_entries,
        'start_date': start_date,
        'end_date': end_date,
        'opening_balance': opening_balance,
        'closing_balance': closing_balance,
        'total_receipts': total_receipts,
        'total_payments': total_payments,
        'net_movement': net_movement,
        'transaction_count': len(all_transactions),
    }
    return render(request, 'ledger/cashbook/cashbook.html', context)