from rest_framework import serializers
from django.utils import timezone
from .models import BankAccount, VirtualCard, Transaction, FundingMethod, ProductRecommendation, USSDSession

class BankAccountSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    is_activated = serializers.SerializerMethodField()
    
    class Meta:
        model = BankAccount
        fields = (
            'id', 'user', 'user_email', 'user_phone', 'account_number',
            'account_type', 'account_name', 'tier_level', 'status', 'balance',
            'available_balance', 'daily_limit', 'single_transaction_limit',
            'created_at', 'activated_at', 'is_activated'
        )
        read_only_fields = (
            'id', 'user', 'account_number', 'balance', 'available_balance',
            'created_at', 'activated_at'
        )
    
    def get_is_activated(self, obj):
        return obj.status == 'active'

class VirtualCardSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    masked_card_number = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = VirtualCard
        fields = (
            'id', 'account', 'account_number', 'card_type', 'masked_card_number',
            'expiry_month', 'expiry_year', 'daily_limit', 'monthly_limit',
            'is_international', 'status', 'is_default', 'is_expired',
            'created_at'
        )
        read_only_fields = ('id', 'account', 'card_number', 'cvv', 'created_at')
    
    def get_masked_card_number(self, obj):
        return obj.mask_card_number()
    
    def get_is_expired(self, obj):
        return obj.is_expired()

class TransactionSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    
    class Meta:
        model = Transaction
        fields = (
            'id', 'account', 'account_number', 'transaction_type', 'amount',
            'narration', 'reference', 'beneficiary_name', 'beneficiary_account',
            'beneficiary_bank', 'status', 'balance_after', 'created_at',
            'completed_at'
        )
        read_only_fields = (
            'id', 'account', 'reference', 'status', 'balance_after',
            'created_at', 'completed_at'
        )

class FundingMethodSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = FundingMethod
        fields = (
            'id', 'user', 'user_email', 'method_type', 'is_active',
            'details', 'verification_required', 'is_verified',
            'created_at'
        )
        read_only_fields = ('id', 'user', 'created_at')

class ProductRecommendationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    is_eligible = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductRecommendation
        fields = (
            'id', 'user', 'user_email', 'product_type', 'title', 'description',
            'eligibility_score', 'amount_offered', 'interest_rate', 'tenure',
            'monthly_repayment', 'is_accepted', 'is_expired', 'is_eligible',
            'created_at', 'expires_at', 'days_remaining'
        )
        read_only_fields = ('id', 'user', 'created_at')
    
    def get_is_eligible(self, obj):
        return obj.is_eligible()
    
    def get_days_remaining(self, obj):
        if obj.expires_at:
            remaining = obj.expires_at - timezone.now()
            return max(0, remaining.days)
        return 0

class USSDSessionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    account_number = serializers.CharField(source='account.account_number', read_only=True)
    
    class Meta:
        model = USSDSession
        fields = (
            'id', 'user', 'user_email', 'account', 'account_number',
            'session_id', 'amount', 'ussd_code', 'bank_name', 'status',
            'is_completed', 'created_at', 'completed_at'
        )
        read_only_fields = ('id', 'user', 'account', 'created_at', 'completed_at')

class AccountCreationSerializer(serializers.Serializer):
    """Serializer for creating a new bank account"""
    account_type = serializers.ChoiceField(choices=BankAccount.ACCOUNT_TYPES)
    initial_funding_method = serializers.ChoiceField(
        choices=[('none', 'None'), ('transfer', 'Bank Transfer'), ('ussd', 'USSD')],
        required=False,
        default='none'
    )
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        # Check if user is verified
        if not user.is_verified:
            raise serializers.ValidationError("User must be verified before creating an account")
        
        # Check if user already has an active account of this type
        if BankAccount.objects.filter(user=user, account_type=attrs['account_type'], status='active').exists():
            raise serializers.ValidationError(f"You already have an active {attrs['account_type']} account")
        
        return attrs

class FundAccountSerializer(serializers.Serializer):
    """Serializer for funding an account"""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=100.00)  # Minimum 100 Naira
    method = serializers.ChoiceField(choices=FundingMethod.METHOD_TYPES)
    
    # Bank transfer details
    bank_name = serializers.CharField(required=False)
    account_number = serializers.CharField(required=False)
    
    # USSD details
    ussd_code = serializers.CharField(required=False)
    bank_code = serializers.CharField(required=False)
    
    def validate(self, attrs):
        method = attrs['method']
        amount = attrs['amount']
        
        if method == 'bank_transfer' and not attrs.get('bank_name'):
            raise serializers.ValidationError("Bank name is required for bank transfers")
        
        if method == 'ussd' and not attrs.get('ussd_code'):
            raise serializers.ValidationError("USSD code is required for USSD transactions")
        
        # Validate amount based on method
        if method == 'ussd' and amount > 100000.00:  # USSD limit
            raise serializers.ValidationError("USSD transactions cannot exceed ₦100,000")
        
        return attrs

class TransferSerializer(serializers.Serializer):
    """Serializer for bank transfers"""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=100.00)
    beneficiary_account = serializers.CharField(max_length=20)
    beneficiary_bank = serializers.CharField(max_length=100)
    beneficiary_name = serializers.CharField(max_length=255)
    narration = serializers.CharField(max_length=255, required=False, default="Transfer")
    
    def validate(self, attrs):
        amount = attrs['amount']
        request = self.context['request']
        
        # Check if user has sufficient balance
        account = request.user.bank_accounts.filter(status='active').first()
        if not account:
            raise serializers.ValidationError("No active account found")
        
        if not account.can_transact(amount):
            raise serializers.ValidationError("Insufficient balance or transaction limit exceeded")
        
        return attrs