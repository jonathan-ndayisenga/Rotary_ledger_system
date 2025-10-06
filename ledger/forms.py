# ledger/forms.py
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML, Field
from .models import Member, RevenueType, Account, PaymentIn, Supplier, PaymentOut, ExpenseType

class MemberForm(forms.ModelForm):
    CLUB_CHOICES = [
        ('rotaract', 'Rotaract Club'),
        ('rotary', 'Rotary Club'),
        ('other', 'Other'),
    ]

    club = forms.ChoiceField(
        choices=CLUB_CHOICES,
        label='Club',
    )

    pay_registration_fee = forms.BooleanField(
        required=False,
        initial=False,
        label='Pay registration fee now'
    )
    revenue_type = forms.ModelChoiceField(
        queryset=RevenueType.objects.filter(is_active=True),
        required=False,
        label='Fee Type'
    )
    amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        required=False,
        min_value=0,
        label='Amount'
    )
    payment_method = forms.ChoiceField(
        choices=PaymentIn.PAYMENT_METHODS,
        required=False,
        label='Payment Method'
    )
    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label='Account'
    )
    payment_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Payment Date'
    )

    class Meta:
        model = Member
        fields = [
            'name', 'rid', 'contact', 'email', 'residence', 
            'club', 'other_club_name', 'buddy_group'
        ]
        widgets = {
            'contact': forms.TextInput(attrs={'placeholder': 'Enter phone number'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter email address'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'
        
        self.helper.layout = Layout(
            HTML('<h4>Member Information</h4>'),
            Row(
                Column('name', css_class='form-group col-md-6'),
                Column('rid', css_class='form-group col-md-6'),
            ),
            Row(
                Column('contact', css_class='form-group col-md-6'),
                Column('email', css_class='form-group col-md-6'),
            ),
            'residence',
            Row(
                Column('club', css_class='form-group col-md-6'),
                Column('other_club_name', css_class='form-group col-md-6', css_id='div_id_other_club_name'),
            ),
            'buddy_group',
            HTML('<hr><h4>Registration Fee (Optional)</h4>'),
            'pay_registration_fee',
            Div(
                Row(
                    Column('revenue_type', css_class='form-group col-md-4'),
                    Column('amount', css_class='form-group col-md-4'),
                    Column('payment_method', css_class='form-group col-md-4'),
                ),
                Row(
                    Column('account', css_class='form-group col-md-6'),
                    Column('payment_date', css_class='form-group col-md-6'),
                ),
                css_id='payment-fields',
                css_class='border p-3 rounded bg-light'
            ),
            Div(
                Submit('submit', 'Save Member', css_class='btn-primary'),
                HTML('<a href="{% url "member_list" %}" class="btn btn-secondary">Cancel</a>'),
                css_class='form-group mt-4'
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        club = cleaned_data.get('club')
        other_name = cleaned_data.get('other_club_name')

        if club == 'other' and not other_name:
            self.add_error('other_club_name', 'Please specify the name of the other club.')

        pay_fee = cleaned_data.get('pay_registration_fee')
        if pay_fee:
            required_fields = {
                'revenue_type': 'This field is required when paying registration fee.',
                'amount': 'Please enter a valid amount.',
                'payment_method': 'This field is required when paying registration fee.',
                'account': 'This field is required when paying registration fee.',
                'payment_date': 'This field is required when paying registration fee.'
            }
            
            for field, error_message in required_fields.items():
                value = cleaned_data.get(field)
                if not value or (field == 'amount' and value <= 0):
                    self.add_error(field, error_message)
        
        return cleaned_data

class MemberSearchForm(forms.Form):
    name = forms.CharField(required=False, label='Search by Name')
    rid = forms.CharField(required=False, label='Search by RID')
    club = forms.ChoiceField(
        choices=[('', 'All Clubs')] + MemberForm.CLUB_CHOICES,
        required=False,
        label='Filter by Club'
    )
    buddy_group = forms.CharField(required=False, label='Filter by Buddy Group')

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'supplier_id', 'contact', 'email', 'address', 'bank_details']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'bank_details': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'
        
        self.helper.layout = Layout(
            HTML('<h4>Supplier Information</h4>'),
            Row(
                Column('name', css_class='form-group col-md-6'),
                Column('supplier_id', css_class='form-group col-md-6'),
            ),
            Row(
                Column('contact', css_class='form-group col-md-6'),
                Column('email', css_class='form-group col-md-6'),
            ),
            'address',
            'bank_details',
            Div(
                Submit('submit', 'Save Supplier', css_class='btn-primary'),
                HTML('<a href="{% url "supplier_list" %}" class="btn btn-secondary">Cancel</a>'),
                css_class='form-group mt-4'
            )
        )

class SupplierSearchForm(forms.Form):
    name = forms.CharField(required=False, label='Search by Name')
    supplier_id = forms.CharField(required=False, label='Search by Supplier ID')
    contact = forms.CharField(required=False, label='Search by Contact')

class PaymentInForm(forms.ModelForm):
    member = forms.ModelChoiceField(
        queryset=Member.objects.all(),
        required=False,
        label="Select Member",
        empty_label="-- Select a Member --",
    )
    
    manual_payer_name = forms.CharField(
        required=False,
        label="Or Enter Payer Name",
        help_text="Use if payer is not a registered member"
    )

    class Meta:
        model = PaymentIn
        fields = [
            'member', 'manual_payer_name', 'revenue_type', 'amount', 
            'payment_date', 'payment_method', 'account', 'notes'
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter payment notes...'}),
            'amount': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }
        labels = {
            'notes': 'Notes',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'
        
        self.helper.layout = Layout(
            HTML('<h4>Record Payment In</h4>'),
            HTML('<h5>Payer Information</h5>'),
            Row(
                Column('member', css_class='form-group col-md-6'),
                Column('manual_payer_name', css_class='form-group col-md-6'),
            ),
            HTML('<hr><h5>Payment Details</h5>'),
            Row(
                Column('revenue_type', css_class='form-group col-md-6'),
                Column('amount', css_class='form-group col-md-6'),
            ),
            Row(
                Column('payment_date', css_class='form-group col-md-6'),
                Column('payment_method', css_class='form-group col-md-6'),
            ),
            Row(
                Column('account', css_class='form-group col-md-6'),
            ),
            'notes',
            Div(
                Submit('submit', 'Record Payment', css_class='btn-primary'),
                HTML('<a href="{% url "payment_in_list" %}" class="btn btn-secondary">Cancel</a>'),
                css_class='form-group mt-4'
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        member = cleaned_data.get('member')
        manual_payer_name = cleaned_data.get('manual_payer_name')
        
        if not member and not manual_payer_name:
            raise forms.ValidationError(
                "You must either select a member or enter a payer name manually."
            )
        
        if member and manual_payer_name:
            self.add_error('manual_payer_name', 
                         "Please use either member selection OR manual entry, not both.")
        
        return cleaned_data

    def save(self, commit=True):
        payment = super().save(commit=False)
        manual_payer_name = self.cleaned_data.get('manual_payer_name')
        
        if manual_payer_name:
            payment.payer_member = None
            payment.payer_name = manual_payer_name
            payment.contact = ''
            payment.email = ''
        else:
            member = self.cleaned_data.get('member')
            if member:
                payment.payer_member = member
                payment.payer_name = member.name
                payment.contact = member.contact
                payment.email = member.email
        
        if commit:
            payment.save()
        return payment

class PaymentInSearchForm(forms.Form):
    PAYMENT_DATE_RANGE = [
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('year', 'This Year'),
        ('custom', 'Custom Date Range'),
    ]
    
    payer_name = forms.CharField(required=False, label='Search by Payer Name')
    receipt_number = forms.CharField(required=False, label='Search by Receipt Number')
    revenue_type = forms.ModelChoiceField(
        queryset=RevenueType.objects.filter(is_active=True),
        required=False,
        label='Filter by Revenue Type'
    )
    payment_date_range = forms.ChoiceField(
        choices=[('', 'All Time')] + PAYMENT_DATE_RANGE,
        required=False,
        label='Date Range'
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='From Date'
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='To Date'
    )

class PaymentOutForm(forms.ModelForm):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        required=False,
        label="Select Supplier",
        empty_label="-- Select a Supplier --",
    )
    
    manual_payee_name = forms.CharField(
        required=False,
        label="Or Enter Payee Name",
        help_text="Use if payee is not a registered supplier"
    )

    class Meta:
        model = PaymentOut
        fields = [
            'supplier', 'manual_payee_name', 'expense_type', 'amount', 
            'payment_date', 'payment_method', 'account', 'reason',
            'invoice_number'
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter payment reason...'}),
            'amount': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'invoice_number': forms.TextInput(attrs={'placeholder': 'Optional invoice/reference number'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'
        
        self.helper.layout = Layout(
            HTML('<h4>Record Payment Out</h4>'),
            HTML('<h5>Payee Information</h5>'),
            Row(
                Column('supplier', css_class='form-group col-md-6'),
                Column('manual_payee_name', css_class='form-group col-md-6'),
            ),
            HTML('<hr><h5>Payment Details</h5>'),
            Row(
                Column('expense_type', css_class='form-group col-md-6'),
                Column('amount', css_class='form-group col-md-6'),
            ),
            Row(
                Column('payment_date', css_class='form-group col-md-6'),
                Column('payment_method', css_class='form-group col-md-6'),
            ),
            Row(
                Column('account', css_class='form-group col-md-6'),
                Column('invoice_number', css_class='form-group col-md-6'),
            ),
            'reason',
            Div(
                Submit('submit', 'Record Payment', css_class='btn-primary'),
                HTML('<a href="{% url "payment_out_list" %}" class="btn btn-secondary">Cancel</a>'),
                css_class='form-group mt-4'
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        supplier = cleaned_data.get('supplier')
        manual_payee_name = cleaned_data.get('manual_payee_name')
        
        if not supplier and not manual_payee_name:
            raise forms.ValidationError(
                "You must either select a supplier or enter a payee name manually."
            )
        
        if supplier and manual_payee_name:
            self.add_error('manual_payee_name', 
                         "Please use either supplier selection OR manual entry, not both.")
        
        return cleaned_data

    def save(self, commit=True):
        payment = super().save(commit=False)
        manual_payee_name = self.cleaned_data.get('manual_payee_name')
        
        if manual_payee_name:
            payment.payee_supplier = None
            payment.payee_name = manual_payee_name
            payment.contact = ''
            payment.email = ''
        else:
            supplier = self.cleaned_data.get('supplier')
            if supplier:
                payment.payee_supplier = supplier
                payment.payee_name = supplier.name
                payment.contact = supplier.contact
                payment.email = supplier.email
        
        if commit:
            payment.save()
        return payment

class PaymentOutSearchForm(forms.Form):
    PAYMENT_DATE_RANGE = [
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('year', 'This Year'),
        ('custom', 'Custom Date Range'),
    ]
    
    payee_name = forms.CharField(required=False, label='Search by Payee Name')
    invoice_number = forms.CharField(required=False, label='Search by Invoice Number')
    expense_type = forms.ModelChoiceField(
        queryset=ExpenseType.objects.filter(is_active=True),
        required=False,
        label='Filter by Expense Type'
    )
    payment_date_range = forms.ChoiceField(
        choices=[('', 'All Time')] + PAYMENT_DATE_RANGE,
        required=False,
        label='Date Range'
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='From Date'
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='To Date'
    )

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'account_type', 'account_number', 'bank_name', 'balance', 'is_active']
        widgets = {
            'balance': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            HTML('<h4>Account Information</h4>'),
            Row(
                Column('name', css_class='form-group col-md-6'),
                Column('account_type', css_class='form-group col-md-6'),
            ),
            Row(
                Column('bank_name', css_class='form-group col-md-6'),
                Column('account_number', css_class='form-group col-md-6'),
            ),
            'balance',
            'is_active',
            Div(
                Submit('submit', 'Save Account', css_class='btn-primary'),
                HTML('<a href="{% url "account_list" %}" class="btn btn-secondary">Cancel</a>'),
                css_class='form-group mt-4'
            )
        )