from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.validators import RegexValidator
from users.models import CustomUser

class BankAccount(models.Model):
    ACCOUNT_TYPES = [
        ('savings', 'Savings Account'),
        ('current', 'Current Account'),
        ('domiciliary', 'Domiciliary Account'),
    ]
    
    ACCOUNT_STATUS = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed'),
    ]
    
    TIER_LEVELS = [
        (1, 'Tier 1 - Basic'),
        (2, 'Tier 2 - Intermediate'),
        (3, 'Tier 3 - Full'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bank_accounts')
    account_number = models.CharField(max_length=10, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='savings')
    account_name = models.CharField(max_length=255)
    
    # Account Details
    tier_level = models.IntegerField(choices=TIER_LEVELS, default=1)
    status = models.CharField(max_length=20, choices=ACCOUNT_STATUS, default='pending')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Limits based on tier
    daily_limit = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
    single_transaction_limit = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'bank_accounts'
        verbose_name = 'Bank Account'
        verbose_name_plural = 'Bank Accounts'
        indexes = [
            models.Index(fields=['account_number']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['tier_level']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.account_number} - {self.user.email}"
    
    def activate_account(self):
        """Activate the account after successful verification"""
        if self.status == 'pending' and self.user.is_verified:
            self.status = 'active'
            self.activated_at = timezone.now()
            self.tier_level = 3  # Full KYC tier
            self.save()
    
    def can_transact(self, amount):
        """Check if account can perform transaction"""
        return (
            self.status == 'active' and
            amount <= self.available_balance and
            amount <= self.single_transaction_limit
        )

class VirtualCard(models.Model):
    CARD_TYPES = [
        ('virtual', 'Virtual Debit Card'),
        ('physical', 'Physical Card'),
    ]
    
    CARD_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blocked', 'Blocked'),
        ('expired', 'Expired'),
    ]
    
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='virtual_cards')
    card_type = models.CharField(max_length=10, choices=CARD_TYPES, default='virtual')
    
    # Card Details
    card_number = models.CharField(max_length=16, unique=True)
    expiry_month = models.CharField(max_length=2)
    expiry_year = models.CharField(max_length=4)
    cvv = models.CharField(max_length=3)
    
    # Card Limits
    daily_limit = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00)
    monthly_limit = models.DecimalField(max_digits=12, decimal_places=2, default=500000.00)
    is_international = models.BooleanField(default=False)
    
    # Status
    status = models.CharField(max_length=10, choices=CARD_STATUS, default='active')
    is_default = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'virtual_cards'
        verbose_name = 'Virtual Card'
        verbose_name_plural = 'Virtual Cards'
        indexes = [
            models.Index(fields=['card_number']),
            models.Index(fields=['account', 'status']),
        ]
    
    def __str__(self):
        return f"Card {self.card_number[-4:]} - {self.account.account_number}"
    
    def mask_card_number(self):
        """Return masked card number for display"""
        return f"**** **** **** {self.card_number[-4:]}"
    
    def is_expired(self):
        """Check if card is expired"""
        current_year = timezone.now().year
        current_month = timezone.now().month
        return (int(self.expiry_year) < current_year or 
                (int(self.expiry_year) == current_year and int(self.expiry_month) < current_month))

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('transfer', 'Bank Transfer'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('ussd', 'USSD Transaction'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]
    
    # Account involved
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    
    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    narration = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, unique=True)
    
    # Counterparty (for transfers)
    beneficiary_name = models.CharField(max_length=255, blank=True)
    beneficiary_account = models.CharField(max_length=20, blank=True)
    beneficiary_bank = models.CharField(max_length=100, blank=True)
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['account', 'created_at']),
            models.Index(fields=['transaction_type', 'status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.reference}"
    
    def mark_completed(self):
        """Mark transaction as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self):
        """Mark transaction as failed"""
        self.status = 'failed'
        self.save()

class FundingMethod(models.Model):
    METHOD_TYPES = [
        ('bank_transfer', 'Bank Transfer'),
        ('ussd', 'USSD'),
        ('card', 'Card Payment'),
        ('wallet', 'Digital Wallet'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='funding_methods')
    method_type = models.CharField(max_length=20, choices=METHOD_TYPES)
    is_active = models.BooleanField(default=True)
    
    # Method-specific details (varies by type)
    details = models.JSONField(default=dict)
    
    # Security
    verification_required = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'funding_methods'
        verbose_name = 'Funding Method'
        verbose_name_plural = 'Funding Methods'
    
    def __str__(self):
        return f"{self.method_type} - {self.user.email}"

class ProductRecommendation(models.Model):
    PRODUCT_TYPES = [
        ('loan', 'Loan Offer'),
        ('savings', 'Savings Plan'),
        ('investment', 'Investment'),
        ('insurance', 'Insurance'),
        ('card_upgrade', 'Card Upgrade'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='product_recommendations')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    
    # Recommendation details
    title = models.CharField(max_length=255)
    description = models.TextField()
    eligibility_score = models.FloatField(validators=[MinValueValidator(0.0)], default=0.0)
    
    # Offer details
    amount_offered = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tenure = models.IntegerField(null=True, blank=True)  # in months
    monthly_repayment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Status
    is_accepted = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'product_recommendations'
        verbose_name = 'Product Recommendation'
        verbose_name_plural = 'Product Recommendations'
        indexes = [
            models.Index(fields=['user', 'product_type']),
            models.Index(fields=['eligibility_score']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-eligibility_score']
    
    def __str__(self):
        return f"{self.product_type} - {self.user.email} - {self.eligibility_score}"
    
    def is_eligible(self):
        """Check if recommendation is still eligible"""
        return self.eligibility_score >= 0.7 and not self.is_expired and timezone.now() < self.expires_at

class USSDSession(models.Model):
    """Track USSD funding sessions"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ussd_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    
    # Session details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    ussd_code = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100)
    
    # Status
    status = models.CharField(max_length=20, choices=Transaction.STATUS_CHOICES, default='pending')
    is_completed = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ussd_sessions'
        verbose_name = 'USSD Session'
        verbose_name_plural = 'USSD Sessions'
    
    def __str__(self):
        return f"USSD {self.bank_name} - {self.amount} - {self.status}"