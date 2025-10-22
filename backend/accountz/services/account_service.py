import random
import string
from django.utils import timezone
from django.db import transaction as db_transaction
from accountz.models import BankAccount, VirtualCard, Transaction, ProductRecommendation  # ← ADD THIS IMPORT

class AccountService:
    """Service for handling bank account operations"""
    
    @staticmethod
    def generate_account_number():
        """Generate unique 10-digit account number"""
        while True:
            # Format: 3 + 7 random digits (Zenith Bank format)
            account_number = '3' + ''.join(random.choices(string.digits, k=7))
            if not BankAccount.objects.filter(account_number=account_number).exists():
                return account_number
    
    @staticmethod
    def generate_card_number():
        """Generate unique 16-digit card number"""
        while True:
            # Format: 4 + 15 random digits (Visa format)
            card_number = '4' + ''.join(random.choices(string.digits, k=15))
            if not VirtualCard.objects.filter(card_number=card_number).exists():
                return card_number
    
    @staticmethod
    def generate_cvv():
        """Generate 3-digit CVV"""
        return ''.join(random.choices(string.digits, k=3))
    
    @staticmethod
    def create_user_account(user, account_type='savings'):
        """Create a new bank account for user"""
        with db_transaction.atomic():
            # Generate account details
            account_number = AccountService.generate_account_number()
            account_name = f"{user.first_name} {user.last_name}"
            
            # Create bank account
            account = BankAccount.objects.create(
                user=user,
                account_number=account_number,
                account_type=account_type,
                account_name=account_name,
                tier_level=3,  # Full KYC tier
                status='active' if user.is_verified else 'pending'
            )
            
            # Create virtual card
            card = AccountService.create_virtual_card(account)
            
            # Activate account if user is verified
            if user.is_verified:
                account.activate_account()
            
            return account, card
    
    @staticmethod
    def create_virtual_card(account):
        """Create virtual card for account"""
        card_number = AccountService.generate_card_number()
        cvv = AccountService.generate_cvv()
        
        # Set expiry 3 years from now
        expiry_date = timezone.now() + timezone.timedelta(days=3*365)
        
        card = VirtualCard.objects.create(
            account=account,
            card_number=card_number,
            cvv=cvv,
            expiry_month=str(expiry_date.month).zfill(2),
            expiry_year=str(expiry_date.year),
            is_default=True
        )
        
        return card
    
    @staticmethod
    def fund_account(account, amount, method='transfer', **kwargs):
        """Fund user account"""
        with db_transaction.atomic():
            # Create transaction record
            transaction = Transaction.objects.create(
                account=account,
                transaction_type='deposit',
                amount=amount,
                narration=f"Account funding via {method}",
                reference=f"FUND_{account.account_number}_{int(timezone.now().timestamp())}",
                status='pending'
            )
            
            try:
                # Update account balance
                account.balance += amount
                account.available_balance += amount
                account.save()
                
                # Mark transaction as completed
                transaction.balance_after = account.balance
                transaction.mark_completed()
                
                return transaction
                
            except Exception as e:
                transaction.mark_failed()
                raise e
    
    @staticmethod
    def process_transfer(from_account, to_account_number, amount, narration="Transfer"):
        """Process bank transfer"""
        with db_transaction.atomic():
            # Check if accounts can transact
            if not from_account.can_transact(amount):
                raise ValueError("Insufficient balance or limit exceeded")
            
            # Get recipient account
            try:
                to_account = BankAccount.objects.get(account_number=to_account_number, status='active')
            except BankAccount.DoesNotExist:
                raise ValueError("Recipient account not found or inactive")
            
            # Create debit transaction
            debit_tx = Transaction.objects.create(
                account=from_account,
                transaction_type='transfer',
                amount=amount,
                narration=narration,
                reference=f"TX_{from_account.account_number}_{int(timezone.now().timestamp())}",
                beneficiary_account=to_account_number,
                beneficiary_name=to_account.account_name,
                status='pending'
            )
            
            # Create credit transaction
            credit_tx = Transaction.objects.create(
                account=to_account,
                transaction_type='deposit',
                amount=amount,
                narration=f"Transfer from {from_account.account_number}",
                reference=f"RX_{to_account.account_number}_{int(timezone.now().timestamp())}",
                status='pending'
            )
            
            try:
                # Update balances
                from_account.balance -= amount
                from_account.available_balance -= amount
                from_account.save()
                
                to_account.balance += amount
                to_account.available_balance += amount
                to_account.save()
                
                # Mark transactions as completed
                debit_tx.balance_after = from_account.balance
                debit_tx.mark_completed()
                
                credit_tx.balance_after = to_account.balance
                credit_tx.mark_completed()
                
                return debit_tx
                
            except Exception as e:
                debit_tx.mark_failed()
                credit_tx.mark_failed()
                raise e

class ProductRecommendationService:
    """Service for generating product recommendations"""
    
    @staticmethod
    def generate_recommendations(user):
        """Generate personalized product recommendations for user"""
        recommendations = []
        
        # Get user data for recommendation engine
        user_profile = user.profile
        accounts = user.bank_accounts.filter(status='active')
        
        # Loan recommendations
        loan_recommendation = ProductRecommendationService._generate_loan_offer(user, accounts)
        if loan_recommendation:
            recommendations.append(loan_recommendation)
        
        # Savings recommendations
        savings_recommendation = ProductRecommendationService._generate_savings_plan(user, accounts)
        if savings_recommendation:
            recommendations.append(savings_recommendation)
        
        # Card upgrade recommendations
        card_recommendation = ProductRecommendationService._generate_card_upgrade(user, accounts)
        if card_recommendation:
            recommendations.append(card_recommendation)
        
        # Save recommendations to database
        for recommendation in recommendations:
            recommendation.save()
        
        return recommendations
    
    @staticmethod
    def _generate_loan_offer(user, accounts):
        """Generate loan offer based on user profile and account activity"""
        # Basic eligibility check
        if not accounts.exists():
            return None
        
        account = accounts.first()
        
        # Calculate eligibility score (simplified)
        eligibility_score = 0.0
        
        # Factors: Account age, balance, transaction history
        account_age = (timezone.now() - account.created_at).days
        if account_age > 30:
            eligibility_score += 0.3
        
        if account.balance > 10000:
            eligibility_score += 0.4
        
        # User employment status
        if hasattr(user, 'profile') and user.profile.occupation:
            eligibility_score += 0.3
        
        if eligibility_score >= 0.7:
            return ProductRecommendation(
                user=user,
                product_type='loan',
                title="Instant Personal Loan",
                description="Get instant access to funds with competitive rates",
                eligibility_score=eligibility_score,
                amount_offered=min(account.balance * 3, 500000),  # Up to 3x balance or 500k
                interest_rate=15.0,  # 15% annual
                tenure=12,  # 12 months
                monthly_repayment=0,  # Calculate based on amount and rate
                expires_at=timezone.now() + timezone.timedelta(days=30)
            )
        
        return None
    
    @staticmethod
    def _generate_savings_plan(user, accounts):
        """Generate savings plan recommendations"""
        if not accounts.exists():
            return None
        
        account = accounts.first()
        
        # Simple savings recommendation
        return ProductRecommendation(
            user=user,
            product_type='savings',
            title="Smart Savings Plan",
            description="Automate your savings and earn higher interest",
            eligibility_score=0.8,
            expires_at=timezone.now() + timezone.timedelta(days=30)
        )
    
    @staticmethod
    def _generate_card_upgrade(user, accounts):
        """Generate card upgrade recommendations"""
        if not accounts.exists():
            return None
        
        account = accounts.first()
        
        if account.balance > 50000:
            return ProductRecommendation(
                user=user,
                product_type='card_upgrade',
                title="Premium Card Upgrade",
                description="Upgrade to our premium card with higher limits and benefits",
                eligibility_score=0.9,
                expires_at=timezone.now() + timezone.timedelta(days=30)
            )
        
        return None