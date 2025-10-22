from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import CustomUser

class PlatformType(models.TextChoices):
    MOBILE = 'mobile', 'Mobile App'
    WEB = 'web', 'Web Browser'
    DESKTOP = 'desktop', 'Desktop Application'

class BehavioralBiometrics(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='biometrics')
    session_id = models.CharField(max_length=100)
    
    # Keystroke Dynamics
    typing_pattern = models.JSONField(default=dict)  # {key_hold_times: [], flight_times: [], rhythm: []}
    touch_patterns = models.JSONField(default=dict)  # {swipe_speeds: [], touch_pressures: [], gesture_patterns: []}
    device_characteristics = models.JSONField(default=dict)  # {device_id: '', os: '', screen_size: '', sensors: []}
    
    # Behavioral Signature
    biometric_signature = models.TextField(blank=True)  # Hashed behavioral fingerprint
    confidence_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    # Session Context
    is_active = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    platform = models.CharField(max_length=10, choices=PlatformType.choices, default=PlatformType.MOBILE)
    browser_fingerprint = models.TextField(blank=True)  # For web platform
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'behavioral_biometrics'
        verbose_name = 'Behavioral Biometric'
        verbose_name_plural = 'Behavioral Biometrics'
        indexes = [
            models.Index(fields=['user', 'session_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['biometric_signature']),
            models.Index(fields=['platform']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Biometrics - {self.user.email} - {self.session_id}"
    
    def calculate_confidence(self):
        """Calculate confidence score based on available biometric data"""
        factors = []
        
        # Typing pattern confidence
        if self.typing_pattern.get('key_hold_times'):
            factors.append(0.4)
        
        # Touch patterns confidence
        if self.touch_patterns.get('swipe_speeds') or self.touch_patterns.get('touch_pressures'):
            factors.append(0.3)
        
        # Device characteristics confidence
        if self.device_characteristics.get('device_id'):
            factors.append(0.3)
        
        if factors:
            self.confidence_score = sum(factors) / len(factors)
        else:
            self.confidence_score = 0.0
        
        return self.confidence_score

class WebBehavioralData(models.Model):
    """Specific behavioral data for web platform"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='web_behavior')
    session_id = models.CharField(max_length=100)
    
    # Mouse/Trackpad behavior
    mouse_movements = models.JSONField(default=dict)  # {speeds: [], patterns: [], click_hold_times: []}
    scroll_behavior = models.JSONField(default=dict)  # {speeds: [], patterns: [], directions: []}
    
    # Keyboard behavior (enhanced for web)
    form_filling_patterns = models.JSONField(default=dict)  # {field_switch_times: [], correction_patterns: []}
    focus_behavior = models.JSONField(default=dict)  # {tab_usage: [], field_skip_patterns: []}
    
    # Browser-specific data
    browser_events = models.JSONField(default=dict)  # {page_switch_times: [], tab_behavior: []}
    timing_patterns = models.JSONField(default=dict)  # {page_load_reaction: [], interaction_delays: []}
    
    # Device characteristics for web
    screen_resolution = models.CharField(max_length=20, blank=True)
    browser_type = models.CharField(max_length=50, blank=True)
    plugins = models.JSONField(default=list)
    
    confidence_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'web_behavioral_data'
        verbose_name = 'Web Behavioral Data'
        verbose_name_plural = 'Web Behavioral Data'
        
class CrossPlatformProfile(models.Model):
    """Unified profile that works across all platforms"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cross_platform_profile')
    
    # Cross-platform behavioral patterns
    interaction_rhythm = models.JSONField(default=dict)  # Common patterns across platforms
    typical_session_duration = models.FloatField(default=0.0)  # In seconds
    preferred_platforms = models.JSONField(default=list)  # ['web', 'mobile', 'desktop']
    
    # Platform-specific adaptations
    mobile_profile = models.JSONField(default=dict)
    web_profile = models.JSONField(default=dict)
    desktop_profile = models.JSONField(default=dict)
    
    # Cross-platform verification
    cross_platform_confidence = models.FloatField(default=0.0)
    last_cross_platform_sync = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cross_platform_profiles'

class BiometricSession(models.Model):
    SESSION_TYPES = [
        ('onboarding', 'Onboarding'),
        ('login', 'Login'),
        ('transaction', 'Transaction'),
        ('continuous', 'Continuous Authentication'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='biometric_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES)
    
    # Session Metrics
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Security Context
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    location_data = models.JSONField(default=dict, blank=True)  # {country: '', city: '', coordinates: ''}
    
    # Performance Metrics
    data_points_collected = models.IntegerField(default=0)
    average_confidence = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'biometric_sessions'
        verbose_name = 'Biometric Session'
        verbose_name_plural = 'Biometric Sessions'
        indexes = [
            models.Index(fields=['user', 'session_type']),
            models.Index(fields=['session_id']),
            models.Index(fields=['start_time']),
        ]
    
    def __str__(self):
        return f"Session - {self.user.email} - {self.session_type}"

class BiometricProfile(models.Model):
    """Consolidated behavioral profile for each user"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='biometric_profile')
    
    # Typing Behavior
    avg_typing_speed = models.FloatField(default=0.0)  # Characters per minute
    typical_hold_times = models.JSONField(default=dict)  # {character: avg_hold_time}
    typical_flight_times = models.JSONField(default=dict)  # Time between key presses
    
    # Touch Behavior
    avg_swipe_speed = models.FloatField(default=0.0)
    typical_touch_pressure = models.FloatField(default=0.0)
    common_gestures = models.JSONField(default=list)
    
    # Device Patterns
    trusted_devices = models.JSONField(default=list)  # List of trusted device IDs
    typical_locations = models.JSONField(default=list)  # Common login locations
    
    # Behavioral Signature
    master_biometric_hash = models.TextField(blank=True)
    profile_confidence = models.FloatField(default=0.0)
    
    # Statistics
    samples_collected = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'biometric_profiles'
        verbose_name = 'Biometric Profile'
        verbose_name_plural = 'Biometric Profiles'
    
    def __str__(self):
        return f"Profile - {self.user.email}"

class BiometricVerificationLog(models.Model):
    VERIFICATION_TYPES = [
        ('login', 'Login Attempt'),
        ('transaction', 'Transaction Auth'),
        ('continuous', 'Continuous Auth'),
        ('challenge', 'Challenge Response'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('suspicious', 'Suspicious'),
        ('inconclusive', 'Inconclusive'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='verification_logs')
    session = models.ForeignKey(BiometricSession, on_delete=models.CASCADE, null=True, blank=True)
    
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Verification Metrics
    confidence_score = models.FloatField()
    risk_score = models.FloatField()  # 0.0 (low risk) to 1.0 (high risk)
    anomaly_detected = models.BooleanField(default=False)
    
    # Context Data
    biometric_data = models.JSONField(default=dict)  # Raw biometric data for this verification
    device_fingerprint = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'biometric_verification_logs'
        verbose_name = 'Biometric Verification Log'
        verbose_name_plural = 'Biometric Verification Logs'
        indexes = [
            models.Index(fields=['user', 'verification_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['risk_score']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Verification - {self.user.email} - {self.verification_type} - {self.status}"