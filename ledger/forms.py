# ledger/forms.py
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML
from .models import Member, RevenueType, Account, PaymentIn

class MemberForm(forms.ModelForm):
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
                Column('buddy_group', css_class='form-group col-md-6'),
            ),
            
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
        pay_fee = cleaned_data.get('pay_registration_fee')
        
        if pay_fee:
            revenue_type = cleaned_data.get('revenue_type')
            amount = cleaned_data.get('amount')
            payment_method = cleaned_data.get('payment_method')
            account = cleaned_data.get('account')
            payment_date = cleaned_data.get('payment_date')
            
            if not revenue_type:
                self.add_error('revenue_type', 'This field is required when paying registration fee.')
            if not amount or amount <= 0:
                self.add_error('amount', 'Please enter a valid amount.')
            if not payment_method:
                self.add_error('payment_method', 'This field is required when paying registration fee.')
            if not account:
                self.add_error('account', 'This field is required when paying registration fee.')
            if not payment_date:
                self.add_error('payment_date', 'This field is required when paying registration fee.')
        
        return cleaned_data

class MemberSearchForm(forms.Form):
    name = forms.CharField(required=False, label='Search by Name')
    rid = forms.CharField(required=False, label='Search by RID')
    club = forms.ChoiceField(
        choices=[('', 'All Clubs')] + Member.CLUB_CHOICES,
        required=False,
        label='Filter by Club'
    )
    buddy_group = forms.CharField(required=False, label='Filter by Buddy Group')