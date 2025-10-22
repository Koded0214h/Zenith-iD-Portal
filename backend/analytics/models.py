from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from users.models import CustomUser
from accountz.models import BankAccount, Transaction, ProductRecommendation
from verification.models import IDVerification, FacialVerification
from biometrics.models import BiometricVerificationLog

class OnboardingFunnel(models.Model):
    """Track user progression through onboarding steps"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='onboarding_funnel')
    
    # Step completion timestamps
    registration_completed_at = models.DateTimeField(null=True, blank=True)
    id_verification_started_at = models.DateTimeField(null=True, blank=True)
    id_verification_completed_at = models.DateTimeField(null=True, blank=True)
    facial_verification_started_at = models.DateTimeField(null=True, blank=True)
    facial_verification_completed_at = models.DateTimeField(null=True, blank=True)
    account_created_at = models.DateTimeField(null=True, blank=True)
    first_funding_at = models.DateTimeField(null=True, blank=True)
    
    # Step durations (in seconds)
    registration_duration = models.FloatField(default=0.0)
    id_verification_duration = models.FloatField(default=0.0)
    facial_verification_duration = models.FloatField(default=0.0)
    total_onboarding_duration = models.FloatField(default=0.0)
    
    # Completion status
    is_completed = models.BooleanField(default=False)
    dropped_off_at = models.CharField(max_length=50, blank=True)  # Which step user dropped off
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'onboarding_funnels'
        verbose_name = 'Onboarding Funnel'
        verbose_name_plural = 'Onboarding Funnels'
    
    def __str__(self):
        return f"Onboarding - {self.user.email}"
    
    def calculate_durations(self):
        """Calculate time spent on each step"""
        if self.registration_completed_at and self.id_verification_started_at:
            self.registration_duration = (self.id_verification_started_at - self.registration_completed_at).total_seconds()
        
        if self.id_verification_completed_at and self.id_verification_started_at:
            self.id_verification_duration = (self.id_verification_completed_at - self.id_verification_started_at).total_seconds()
        
        if self.facial_verification_completed_at and self.facial_verification_started_at:
            self.facial_verification_duration = (self.facial_verification_completed_at - self.facial_verification_started_at).total_seconds()
        
        if self.account_created_at and self.registration_completed_at:
            self.total_onboarding_duration = (self.account_created_at - self.registration_completed_at).total_seconds()
        
        self.save()

class UserBehaviorEvent(models.Model):
    """Track user behavior events across the platform"""
    EVENT_TYPES = [
        ('app_open', 'App Open'),
        ('screen_view', 'Screen View'),
        ('button_click', 'Button Click'),
        ('form_submit', 'Form Submit'),
        ('transaction_initiated', 'Transaction Initiated'),
        ('product_view', 'Product View'),
        ('recommendation_click', 'Recommendation Click'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='behavior_events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    event_name = models.CharField(max_length=100)  # e.g., 'login_button_click'
    
    # Event context
    screen_name = models.CharField(max_length=100, blank=True)
    element_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict)  # Additional event data
    
    # Session context
    session_id = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_behavior_events'
        verbose_name = 'User Behavior Event'
        verbose_name_plural = 'User Behavior Events'
        indexes = [
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['event_type', 'event_name']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.user.email} - {self.created_at}"

class ProductPerformance(models.Model):
    """Track performance of product recommendations"""
    product_recommendation = models.ForeignKey(ProductRecommendation, on_delete=models.CASCADE, related_name='performance_metrics')
    
    # Engagement metrics
    views_count = models.IntegerField(default=0)
    clicks_count = models.IntegerField(default=0)
    conversions_count = models.IntegerField(default=0)
    
    # Performance metrics
    click_through_rate = models.FloatField(default=0.0)  # clicks/views
    conversion_rate = models.FloatField(default=0.0)     # conversions/clicks
    
    # Revenue metrics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    average_revenue_per_conversion = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Time period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_performance'
        verbose_name = 'Product Performance'
        verbose_name_plural = 'Product Performance Metrics'
        indexes = [
            models.Index(fields=['product_recommendation', 'period_start']),
        ]
    
    def __str__(self):
        return f"Performance - {self.product_recommendation.product_type}"

class RiskAnalytics(models.Model):
    """Analytics for risk and security monitoring"""
    RISK_TYPES = [
        ('verification_fraud', 'Verification Fraud'),
        ('transaction_fraud', 'Transaction Fraud'),
        ('account_takeover', 'Account Takeover'),
        ('synthetic_identity', 'Synthetic Identity'),
    ]
    
    risk_type = models.CharField(max_length=50, choices=RISK_TYPES)
    
    # Risk metrics
    detected_cases = models.IntegerField(default=0)
    prevented_cases = models.IntegerField(default=0)
    false_positives = models.IntegerField(default=0)
    
    # Effectiveness metrics
    detection_rate = models.FloatField(default=0.0)
    prevention_rate = models.FloatField(default=0.0)
    false_positive_rate = models.FloatField(default=0.0)
    
    # Financial impact
    potential_loss_prevented = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    actual_loss = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Time period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'risk_analytics'
        verbose_name = 'Risk Analytics'
        verbose_name_plural = 'Risk Analytics'
        indexes = [
            models.Index(fields=['risk_type', 'period_start']),
        ]
    
    def __str__(self):
        return f"Risk - {self.risk_type} - {self.period_start.date()}"

class BusinessMetrics(models.Model):
    """Key business performance indicators"""
    METRIC_TYPES = [
        ('user_acquisition', 'User Acquisition'),
        ('user_activation', 'User Activation'),
        ('revenue', 'Revenue'),
        ('retention', 'Retention'),
        ('engagement', 'Engagement'),
    ]
    
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    metric_name = models.CharField(max_length=100)  # e.g., 'daily_active_users', 'conversion_rate'
    
    # Metric values
    value = models.FloatField()
    target_value = models.FloatField(null=True, blank=True)
    previous_value = models.FloatField(null=True, blank=True)
    
    # Growth metrics
    growth_rate = models.FloatField(default=0.0)  # Percentage growth from previous period
    trend_direction = models.CharField(max_length=10, choices=[('up', 'Up'), ('down', 'Down'), ('stable', 'Stable')])
    
    # Time period
    period = models.CharField(max_length=20, choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')])
    period_date = models.DateField()
    
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'business_metrics'
        verbose_name = 'Business Metric'
        verbose_name_plural = 'Business Metrics'
        indexes = [
            models.Index(fields=['metric_type', 'period_date']),
            models.Index(fields=['metric_name', 'period']),
        ]
        unique_together = ['metric_name', 'period', 'period_date']
    
    def __str__(self):
        return f"{self.metric_name} - {self.period_date}"

class FunnelConversion(models.Model):
    """Track conversion rates through key funnels"""
    FUNNEL_TYPES = [
        ('onboarding', 'User Onboarding'),
        ('verification', 'Identity Verification'),
        ('funding', 'Account Funding'),
        ('product_adoption', 'Product Adoption'),
    ]
    
    funnel_type = models.CharField(max_length=50, choices=FUNNEL_TYPES)
    step_name = models.CharField(max_length=100)
    step_order = models.IntegerField()  # Order in the funnel
    
    # Conversion metrics
    users_entered = models.IntegerField(default=0)
    users_completed = models.IntegerField(default=0)
    dropoffs = models.IntegerField(default=0)
    
    conversion_rate = models.FloatField(default=0.0)
    dropoff_rate = models.FloatField(default=0.0)
    
    # Time metrics
    average_time_in_step = models.FloatField(default=0.0)  # in seconds
    median_time_in_step = models.FloatField(default=0.0)
    
    # Time period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'funnel_conversions'
        verbose_name = 'Funnel Conversion'
        verbose_name_plural = 'Funnel Conversions'
        indexes = [
            models.Index(fields=['funnel_type', 'step_order']),
            models.Index(fields=['period_start']),
        ]
    
    def __str__(self):
        return f"{self.funnel_type} - {self.step_name} - {self.conversion_rate}%"

class UserSegment(models.Model):
    """User segmentation for targeted analytics"""
    SEGMENT_TYPES = [
        ('demographic', 'Demographic'),
        ('behavioral', 'Behavioral'),
        ('value_based', 'Value Based'),
        ('product_usage', 'Product Usage'),
    ]
    
    segment_name = models.CharField(max_length=100)
    segment_type = models.CharField(max_length=50, choices=SEGMENT_TYPES)
    
    # Segment definition
    criteria = models.JSONField(default=dict)  # Rules for segment membership
    user_count = models.IntegerField(default=0)
    
    # Segment performance
    average_ltv = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Lifetime Value
    engagement_score = models.FloatField(default=0.0)
    retention_rate = models.FloatField(default=0.0)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_segments'
        verbose_name = 'User Segment'
        verbose_name_plural = 'User Segments'
        indexes = [
            models.Index(fields=['segment_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.segment_name} ({self.user_count} users)"

class AITrainingData(models.Model):
    """Store data for AI model training and improvement"""
    DATA_TYPES = [
        ('verification_patterns', 'Verification Patterns'),
        ('behavioral_biometrics', 'Behavioral Biometrics'),
        ('product_preferences', 'Product Preferences'),
        ('fraud_patterns', 'Fraud Patterns'),
    ]
    
    data_type = models.CharField(max_length=50, choices=DATA_TYPES)
    data_points = models.JSONField(default=dict)  # Raw training data
    
    # Model performance
    model_version = models.CharField(max_length=50, blank=True)
    accuracy_score = models.FloatField(null=True, blank=True)
    precision_score = models.FloatField(null=True, blank=True)
    recall_score = models.FloatField(null=True, blank=True)
    
    # Metadata
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ai_training_data'
        verbose_name = 'AI Training Data'
        verbose_name_plural = 'AI Training Data'
        indexes = [
            models.Index(fields=['data_type', 'is_processed']),
        ]
    
    def __str__(self):
        return f"{self.data_type} - {self.created_at.date()}"