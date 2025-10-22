from django.contrib import admin
from .models import IDVerification, FacialVerification, GovernmentVerificationLog, VerificationSettings

@admin.register(IDVerification)
class IDVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'id_type', 'id_number', 'status', 'government_verified', 'verification_score', 'created_at')
    list_filter = ('status', 'id_type', 'government_verified', 'created_at')
    search_fields = ('user__email', 'user__phone_number', 'id_number')
    readonly_fields = ('created_at', 'processed_at', 'completed_at')
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'id_type', 'id_number', 'status')
        }),
        ('Document Images', {
            'fields': ('id_image_front', 'id_image_back')
        }),
        ('Verification Results', {
            'fields': ('extracted_data', 'ocr_confidence', 'government_verified', 'verification_score', 'government_response')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at', 'completed_at')
        }),
    )

@admin.register(FacialVerification)
class FacialVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'id_verification', 'status', 'liveness_passed', 'match_passed', 'liveness_score', 'match_score', 'created_at')
    list_filter = ('status', 'liveness_passed', 'match_passed', 'created_at')
    search_fields = ('user__email', 'user__phone_number')
    readonly_fields = ('created_at', 'processed_at')
    raw_id_fields = ('user', 'id_verification')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'id_verification', 'status')
        }),
        ('Facial Images', {
            'fields': ('facial_image', 'id_photo_extracted')
        }),
        ('Verification Scores', {
            'fields': ('liveness_score', 'match_score', 'liveness_passed', 'match_passed')
        }),
        ('Technical Details', {
            'fields': ('landmarks_detected', 'processing_time')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at')
        }),
    )

@admin.register(GovernmentVerificationLog)
class GovernmentVerificationLogAdmin(admin.ModelAdmin):
    list_display = ('id_verification', 'verification_type', 'status', 'response_time', 'created_at')
    list_filter = ('verification_type', 'status', 'created_at')
    search_fields = ('id_verification__user__email', 'id_verification__user__phone_number')
    readonly_fields = ('created_at',)
    raw_id_fields = ('id_verification',)

@admin.register(VerificationSettings)
class VerificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'ocr_confidence_threshold', 'liveness_threshold', 'facial_match_threshold', 'updated_at')
    readonly_fields = ('updated_at',)