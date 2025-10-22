from django.contrib import admin
from .models import BehavioralBiometrics, BiometricSession, BiometricProfile, BiometricVerificationLog

@admin.register(BehavioralBiometrics)
class BehavioralBiometricsAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_id', 'confidence_score', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'confidence_score')
    search_fields = ('user__email', 'user__phone_number', 'session_id')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)

@admin.register(BiometricSession)
class BiometricSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_id', 'session_type', 'is_active', 'start_time', 'data_points_collected')
    list_filter = ('session_type', 'is_active', 'start_time')
    search_fields = ('user__email', 'user__phone_number', 'session_id')
    readonly_fields = ('start_time', 'end_time')
    raw_id_fields = ('user',)

@admin.register(BiometricProfile)
class BiometricProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'samples_collected', 'profile_confidence', 'last_updated')
    list_filter = ('profile_confidence', 'last_updated')
    search_fields = ('user__email', 'user__phone_number')
    readonly_fields = ('last_updated', 'created_at')
    raw_id_fields = ('user',)

@admin.register(BiometricVerificationLog)
class BiometricVerificationLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'verification_type', 'status', 'confidence_score', 'risk_score', 'created_at')
    list_filter = ('verification_type', 'status', 'anomaly_detected', 'created_at')
    search_fields = ('user__email', 'user__phone_number', 'device_fingerprint')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'session')