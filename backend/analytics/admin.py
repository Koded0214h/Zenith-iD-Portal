from django.contrib import admin
from .models import (
    OnboardingFunnel, UserBehaviorEvent, ProductPerformance,
    RiskAnalytics, BusinessMetrics, FunnelConversion, UserSegment, AITrainingData
)

@admin.register(OnboardingFunnel)
class OnboardingFunnelAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_completed', 'total_onboarding_duration', 'dropped_off_at', 'created_at')
    list_filter = ('is_completed', 'dropped_off_at', 'created_at')
    search_fields = ('user__email', 'user__phone_number')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)

@admin.register(UserBehaviorEvent)
class UserBehaviorEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'event_name', 'screen_name', 'created_at')
    list_filter = ('event_type', 'screen_name', 'created_at')
    search_fields = ('user__email', 'event_name', 'screen_name')
    readonly_fields = ('created_at',)

@admin.register(ProductPerformance)
class ProductPerformanceAdmin(admin.ModelAdmin):
    list_display = ('product_recommendation', 'click_through_rate', 'conversion_rate', 'total_revenue', 'period_start')
    list_filter = ('period_start', 'period_end')
    search_fields = ('product_recommendation__title', 'product_recommendation__product_type')
    readonly_fields = ('calculated_at',)

@admin.register(RiskAnalytics)
class RiskAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('risk_type', 'detection_rate', 'prevention_rate', 'false_positive_rate', 'period_start')
    list_filter = ('risk_type', 'period_start')
    readonly_fields = ('calculated_at',)

@admin.register(BusinessMetrics)
class BusinessMetricsAdmin(admin.ModelAdmin):
    list_display = ('metric_name', 'metric_type', 'value', 'growth_rate', 'period', 'period_date')
    list_filter = ('metric_type', 'period', 'period_date')
    search_fields = ('metric_name',)
    readonly_fields = ('calculated_at',)

@admin.register(FunnelConversion)
class FunnelConversionAdmin(admin.ModelAdmin):
    list_display = ('funnel_type', 'step_name', 'conversion_rate', 'dropoff_rate', 'period_start')
    list_filter = ('funnel_type', 'period_start')
    readonly_fields = ('calculated_at',)

@admin.register(UserSegment)
class UserSegmentAdmin(admin.ModelAdmin):
    list_display = ('segment_name', 'segment_type', 'user_count', 'average_ltv', 'is_active')
    list_filter = ('segment_type', 'is_active')
    search_fields = ('segment_name',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(AITrainingData)
class AITrainingDataAdmin(admin.ModelAdmin):
    list_display = ('data_type', 'model_version', 'accuracy_score', 'is_processed', 'created_at')
    list_filter = ('data_type', 'is_processed', 'created_at')
    readonly_fields = ('created_at', 'processed_at')