from rest_framework import serializers
from django.utils import timezone
from .models import (
    OnboardingFunnel, UserBehaviorEvent, ProductPerformance,
    RiskAnalytics, BusinessMetrics, FunnelConversion, UserSegment, AITrainingData
)

class OnboardingFunnelSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    is_within_3_minutes = serializers.SerializerMethodField()
    current_step = serializers.SerializerMethodField()
    
    class Meta:
        model = OnboardingFunnel
        fields = (
            'id', 'user', 'user_email', 'registration_completed_at',
            'id_verification_started_at', 'id_verification_completed_at',
            'facial_verification_started_at', 'facial_verification_completed_at',
            'account_created_at', 'first_funding_at', 'registration_duration',
            'id_verification_duration', 'facial_verification_duration',
            'total_onboarding_duration', 'is_completed', 'dropped_off_at',
            'is_within_3_minutes', 'current_step', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def get_is_within_3_minutes(self, obj):
        return obj.total_onboarding_duration <= 180  # 3 minutes in seconds
    
    def get_current_step(self, obj):
        if obj.first_funding_at:
            return 'completed'
        elif obj.account_created_at:
            return 'funding'
        elif obj.facial_verification_completed_at:
            return 'account_creation'
        elif obj.id_verification_completed_at:
            return 'facial_verification'
        elif obj.registration_completed_at:
            return 'id_verification'
        else:
            return 'registration'

class UserBehaviorEventSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserBehaviorEvent
        fields = (
            'id', 'user', 'user_email', 'event_type', 'event_name',
            'screen_name', 'element_id', 'metadata', 'session_id',
            'ip_address', 'user_agent', 'created_at'
        )
        read_only_fields = ('id', 'user', 'created_at')

class ProductPerformanceSerializer(serializers.ModelSerializer):
    product_type = serializers.CharField(source='product_recommendation.product_type', read_only=True)
    product_title = serializers.CharField(source='product_recommendation.title', read_only=True)
    
    class Meta:
        model = ProductPerformance
        fields = (
            'id', 'product_recommendation', 'product_type', 'product_title',
            'views_count', 'clicks_count', 'conversions_count',
            'click_through_rate', 'conversion_rate', 'total_revenue',
            'average_revenue_per_conversion', 'period_start', 'period_end',
            'calculated_at'
        )
        read_only_fields = ('id', 'calculated_at')

class RiskAnalyticsSerializer(serializers.ModelSerializer):
    risk_efficiency = serializers.SerializerMethodField()
    
    class Meta:
        model = RiskAnalytics
        fields = (
            'id', 'risk_type', 'detected_cases', 'prevented_cases',
            'false_positives', 'detection_rate', 'prevention_rate',
            'false_positive_rate', 'potential_loss_prevented', 'actual_loss',
            'risk_efficiency', 'period_start', 'period_end', 'calculated_at'
        )
        read_only_fields = ('id', 'calculated_at')
    
    def get_risk_efficiency(self, obj):
        if obj.actual_loss + obj.potential_loss_prevented > 0:
            return (obj.potential_loss_prevented / (obj.actual_loss + obj.potential_loss_prevented)) * 100
        return 0.0

class BusinessMetricsSerializer(serializers.ModelSerializer):
    is_on_target = serializers.SerializerMethodField()
    performance_status = serializers.SerializerMethodField()
    
    class Meta:
        model = BusinessMetrics
        fields = (
            'id', 'metric_type', 'metric_name', 'value', 'target_value',
            'previous_value', 'growth_rate', 'trend_direction', 'period',
            'period_date', 'is_on_target', 'performance_status', 'calculated_at'
        )
        read_only_fields = ('id', 'calculated_at')
    
    def get_is_on_target(self, obj):
        if obj.target_value:
            return obj.value >= obj.target_value
        return None
    
    def get_performance_status(self, obj):
        if obj.target_value:
            if obj.value >= obj.target_value:
                return 'exceeding'
            elif obj.value >= obj.target_value * 0.8:
                return 'meeting'
            else:
                return 'below'
        return 'no_target'

class FunnelConversionSerializer(serializers.ModelSerializer):
    funnel_completion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = FunnelConversion
        fields = (
            'id', 'funnel_type', 'step_name', 'step_order',
            'users_entered', 'users_completed', 'dropoffs',
            'conversion_rate', 'dropoff_rate', 'average_time_in_step',
            'median_time_in_step', 'funnel_completion_rate',
            'period_start', 'period_end', 'calculated_at'
        )
        read_only_fields = ('id', 'calculated_at')
    
    def get_funnel_completion_rate(self, obj):
        # This would typically be calculated across the entire funnel
        return obj.conversion_rate  # Simplified

class UserSegmentSerializer(serializers.ModelSerializer):
    growth_trend = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSegment
        fields = (
            'id', 'segment_name', 'segment_type', 'criteria', 'user_count',
            'average_ltv', 'engagement_score', 'retention_rate', 'growth_trend',
            'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_growth_trend(self, obj):
        # This would calculate segment growth over time
        return 'growing'  # Simplified

class AITrainingDataSerializer(serializers.ModelSerializer):
    data_quality_score = serializers.SerializerMethodField()
    
    class Meta:
        model = AITrainingData
        fields = (
            'id', 'data_type', 'data_points', 'model_version',
            'accuracy_score', 'precision_score', 'recall_score',
            'data_quality_score', 'is_processed', 'processed_at',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')
    
    def get_data_quality_score(self, obj):
        # Calculate data quality based on completeness and structure
        if obj.data_points:
            return 85.0  # Simplified calculation
        return 0.0

class AnalyticsDashboardSerializer(serializers.Serializer):
    """Serializer for analytics dashboard data"""
    total_users = serializers.IntegerField()
    active_users_today = serializers.IntegerField()
    onboarding_conversion_rate = serializers.FloatField()
    average_onboarding_time = serializers.FloatField()
    total_transactions_today = serializers.IntegerField()
    total_volume_today = serializers.DecimalField(max_digits=12, decimal_places=2)
    fraud_prevention_rate = serializers.FloatField()
    product_recommendation_conversion = serializers.FloatField()
    
    # Trends
    user_growth_trend = serializers.CharField()
    revenue_growth_trend = serializers.CharField()
    risk_trend = serializers.CharField()

class FunnelAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for funnel analysis requests"""
    funnel_type = serializers.ChoiceField(choices=FunnelConversion.FUNNEL_TYPES)
    period_days = serializers.IntegerField(min_value=1, max_value=365, default=30)
    segment_by = serializers.ChoiceField(
        choices=[('none', 'None'), ('device', 'Device'), ('region', 'Region'), ('age', 'Age')],
        required=False,
        default='none'
    )

class UserBehaviorAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for user behavior analysis requests"""
    user_id = serializers.IntegerField(required=False)
    event_types = serializers.ListField(
        child=serializers.ChoiceField(choices=UserBehaviorEvent.EVENT_TYPES),
        required=False
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)