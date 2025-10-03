# ledger/management/commands/create_initial_data.py
from django.core.management.base import BaseCommand
from ledger.models import RevenueType, Account

class Command(BaseCommand):
    help = 'Create initial revenue types and accounts'

    def handle(self, *args, **options):
        # Create revenue types
        revenue_types = [
            {'name': 'Registration Fee', 'amount_default': 1000.00},
            {'name': 'Monthly Dues', 'amount_default': 500.00},
            {'name': 'Event Registration', 'amount_default': 200.00},
            {'name': 'Donation', 'amount_default': 0.00},
            {'name': 'Project Contribution', 'amount_default': 300.00},
        ]
        
        for rt_data in revenue_types:
            obj, created = RevenueType.objects.get_or_create(
                name=rt_data['name'],
                defaults={'amount_default': rt_data['amount_default']}
            )
            if created:
                self.stdout.write(f'Created revenue type: {rt_data["name"]}')
        
        # Create default accounts
        accounts = [
            {'name': 'Main Cash', 'account_type': 'cash', 'balance': 0},
            {'name': 'Equity Bank', 'account_type': 'bank', 'balance': 0},
            {'name': 'M-Pesa', 'account_type': 'mobile', 'balance': 0},
        ]
        
        for acc_data in accounts:
            obj, created = Account.objects.get_or_create(
                name=acc_data['name'],
                defaults={
                    'account_type': acc_data['account_type'],
                    'balance': acc_data['balance']
                }
            )
            if created:
                self.stdout.write(f'Created account: {acc_data["name"]}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created initial data')
        )