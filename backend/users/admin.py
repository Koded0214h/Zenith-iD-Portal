from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile, UserSession, OTPVerification

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'phone_number', 'first_name', 'last_name', 'is_verified', 'verification_tier', 'is_active', 'date_joined')
    list_filter = ('is_verified', 'verification_tier', 'is_active', 'is_staff')
    search_fields = ('email', 'phone_number', 'first_name', 'last_name', 'nin', 'bvn')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Zenith iD Information', {
            'fields': ('phone_number', 'nin', 'bvn', 'is_verified', 'verification_tier')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Zenith iD Information', {
            'fields': ('phone_number', 'email', 'first_name', 'last_name')
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth', 'occupation', 'marital_status', 'gender')
    list_filter = ('marital_status', 'gender')
    search_fields = ('user__email', 'user__phone_number', 'occupation', 'address')
    raw_id_fields = ('user',)

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'login_time', 'logout_time', 'is_active')
    list_filter = ('is_active', 'login_time')
    search_fields = ('user__email', 'user__phone_number', 'ip_address', 'session_key')
    readonly_fields = ('login_time', 'logout_time')

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_code', 'purpose', 'is_used', 'created_at', 'expires_at')
    list_filter = ('purpose', 'is_used', 'created_at')
    search_fields = ('user__email', 'user__phone_number', 'otp_code')
    readonly_fields = ('created_at', 'expires_at')