from django.contrib import admin
from .models import BankAccount, VirtualCard, Transaction, FundingMethod, ProductRecommendation, USSDSession

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'account_type', 'tier_level', 'status', 'balance', 'created_at')
    list_filter = ('account_type', 'tier_level', 'status', 'created_at')
    search_fields = ('account_number', 'user__email', 'user__phone_number')
    readonly_fields = ('created_at', 'updated_at', 'activated_at')
    raw_id_fields = ('user',)

@admin.register(VirtualCard)
class VirtualCardAdmin(admin.ModelAdmin):
    list_display = ('mask_card_number', 'account', 'card_type', 'status', 'is_default', 'created_at')
    list_filter = ('card_type', 'status', 'is_default', 'created_at')
    search_fields = ('card_number', 'account__account_number')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'account', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('reference', 'account__account_number', 'beneficiary_account')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')

@admin.register(ProductRecommendation)
class ProductRecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'product_type', 'eligibility_score', 'is_accepted', 'is_expired', 'created_at')
    list_filter = ('product_type', 'is_accepted', 'is_expired', 'created_at')
    search_fields = ('user__email', 'user__phone_number', 'title')
    readonly_fields = ('created_at',)

@admin.register(USSDSession)
class USSDSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'amount', 'bank_name', 'status', 'created_at')
    list_filter = ('status', 'bank_name', 'created_at')
    search_fields = ('session_id', 'user__email', 'user__phone_number')
    readonly_fields = ('created_at', 'completed_at')