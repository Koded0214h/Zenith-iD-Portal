from rest_framework import serializers
from django.utils import timezone
from .models import (
    BehavioralBiometrics, BiometricSession, 
    BiometricProfile, BiometricVerificationLog,
    CrossPlatformProfile, WebBehavioralData
)

class BehavioralBiometricsSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = BehavioralBiometrics
        fields = (
            'id', 'user', 'user_email', 'session_id', 'typing_pattern', 
            'touch_patterns', 'device_characteristics', 'biometric_signature',
            'confidence_score', 'is_active', 'ip_address', 'user_agent',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at', 'confidence_score')
    
    def validate_typing_pattern(self, value):
        """Validate typing pattern structure"""
        expected_keys = ['key_hold_times', 'flight_times', 'rhythm']
        if not any(key in value for key in expected_keys):
            raise serializers.ValidationError(
                "Typing pattern must contain at least one of: key_hold_times, flight_times, rhythm"
            )
        return value
    
    def validate_touch_patterns(self, value):
        """Validate touch patterns structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Touch patterns must be a JSON object")
        return value

class BiometricSessionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = BiometricSession
        fields = (
            'id', 'user', 'user_email', 'session_id', 'session_type',
            'start_time', 'end_time', 'is_active', 'ip_address', 'user_agent',
            'location_data', 'data_points_collected', 'average_confidence',
            'duration'
        )
        read_only_fields = ('id', 'user', 'start_time', 'data_points_collected', 'average_confidence')
    
    def get_duration(self, obj):
        if obj.end_time:
            return (obj.end_time - obj.start_time).total_seconds()
        elif obj.is_active:
            return (timezone.now() - obj.start_time).total_seconds()
        return None

class BiometricProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    profile_strength = serializers.SerializerMethodField()
    
    class Meta:
        model = BiometricProfile
        fields = (
            'id', 'user', 'user_email', 'avg_typing_speed', 'typical_hold_times',
            'typical_flight_times', 'avg_swipe_speed', 'typical_touch_pressure',
            'common_gestures', 'trusted_devices', 'typical_locations',
            'master_biometric_hash', 'profile_confidence', 'samples_collected',
            'last_updated', 'created_at', 'profile_strength'
        )
        read_only_fields = ('id', 'user', 'last_updated', 'created_at')
    
    def get_profile_strength(self, obj):
        """Calculate overall profile strength"""
        if obj.samples_collected < 10:
            return 'weak'
        elif obj.samples_collected < 50:
            return 'medium'
        else:
            return 'strong'

class BiometricVerificationLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    session_type = serializers.CharField(source='session.session_type', read_only=True)
    
    class Meta:
        model = BiometricVerificationLog
        fields = (
            'id', 'user', 'user_email', 'session', 'session_type',
            'verification_type', 'status', 'confidence_score', 'risk_score',
            'anomaly_detected', 'biometric_data', 'device_fingerprint',
            'ip_address', 'created_at'
        )
        read_only_fields = ('id', 'user', 'created_at')

class BiometricDataCollectionSerializer(serializers.Serializer):
    """Serializer for collecting biometric data from mobile app"""
    session_id = serializers.CharField(max_length=100)
    
    # Typing data
    key_hold_times = serializers.ListField(
        child=serializers.DictField(), required=False
    )  # [{key: 'a', hold_time: 150}, ...]
    
    flight_times = serializers.ListField(
        child=serializers.FloatField(), required=False
    )  # [time_between_keys, ...]
    
    # Touch data
    swipe_data = serializers.ListField(
        child=serializers.DictField(), required=False
    )  # [{speed: 2.5, distance: 100, direction: 'left'}, ...]
    
    touch_data = serializers.ListField(
        child=serializers.DictField(), required=False
    )  # [{pressure: 0.8, size: 10.5, x: 100, y: 200}, ...]
    
    # Device data
    device_info = serializers.DictField(required=False)
    sensor_data = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    
    def validate(self, attrs):
        """Ensure at least some biometric data is provided"""
        has_typing_data = attrs.get('key_hold_times') or attrs.get('flight_times')
        has_touch_data = attrs.get('swipe_data') or attrs.get('touch_data')
        
        if not (has_typing_data or has_touch_data):
            raise serializers.ValidationError(
                "At least one type of biometric data (typing or touch) must be provided"
            )
        
        return attrs

class BiometricVerificationRequestSerializer(serializers.Serializer):
    """Serializer for biometric verification requests"""
    session_id = serializers.CharField(max_length=100)
    verification_type = serializers.ChoiceField(
        choices=BiometricVerificationLog.VERIFICATION_TYPES
    )
    
    # Current biometric sample
    biometric_sample = serializers.DictField()
    
    # Context data
    device_fingerprint = serializers.CharField(max_length=255)
    ip_address = serializers.IPAddressField()

class VerificationResultSerializer(serializers.Serializer):
    """Serializer for verification results"""
    is_verified = serializers.BooleanField()
    confidence_score = serializers.FloatField()
    risk_score = serializers.FloatField()
    status = serializers.CharField()
    message = serializers.CharField()
    requires_challenge = serializers.BooleanField(default=False)
    challenge_type = serializers.CharField(required=False)  # 'otp', 'questions', 'biometric'
    
    
class WebBehavioralDataSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = WebBehavioralData
        fields = (
            'id', 'user', 'user_email', 'session_id', 'mouse_movements',
            'scroll_behavior', 'form_filling_patterns', 'focus_behavior',
            'browser_events', 'timing_patterns', 'screen_resolution',
            'browser_type', 'plugins', 'confidence_score', 'created_at'
        )
        read_only_fields = ('id', 'user', 'created_at')

class WebDataCollectionSerializer(serializers.Serializer):
    """Serializer for collecting web behavioral data"""
    session_id = serializers.CharField(max_length=100)
    
    # Mouse/trackpad data
    mouse_movements = serializers.ListField(
        child=serializers.DictField(), required=False
    )  # [{x: 100, y: 200, speed: 2.5, timestamp: 123456}, ...]
    
    scroll_events = serializers.ListField(
        child=serializers.DictField(), required=False
    )  # [{delta: 100, speed: 1.5, direction: 'down', timestamp: 123456}, ...]
    
    # Keyboard and form behavior
    keystroke_timing = serializers.ListField(
        child=serializers.DictField(), required=False
    )  # [{key: 'a', hold_time: 150, next_key_delay: 200}, ...]
    
    form_interactions = serializers.ListField(
        child=serializers.DictField(), required=False
    )  # [{field_name: 'email', focus_time: 2000, corrections: 2}, ...]
    
    # Browser behavior
    page_events = serializers.ListField(
        child=serializers.DictField(), required=False
    )  # [{event: 'click', element: 'button', timing: 1500}, ...]
    
    # Device/browser info
    browser_info = serializers.DictField(required=False)
    screen_info = serializers.DictField(required=False)
    
    def validate(self, attrs):
        """Ensure at least some web behavioral data is provided"""
        has_mouse_data = attrs.get('mouse_movements')
        has_scroll_data = attrs.get('scroll_events')
        has_keystroke_data = attrs.get('keystroke_timing')
        
        if not (has_mouse_data or has_scroll_data or has_keystroke_data):
            raise serializers.ValidationError(
                "At least one type of web behavioral data must be provided"
            )
        
        return attrs

class CrossPlatformProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    profile_completeness = serializers.SerializerMethodField()
    
    class Meta:
        model = CrossPlatformProfile
        fields = (
            'id', 'user', 'user_email', 'interaction_rhythm',
            'typical_session_duration', 'preferred_platforms',
            'mobile_profile', 'web_profile', 'desktop_profile',
            'cross_platform_confidence', 'last_cross_platform_sync',
            'profile_completeness'
        )
        read_only_fields = ('id', 'user', 'last_cross_platform_sync')
    
    def get_profile_completeness(self, obj):
        """Calculate how complete the cross-platform profile is"""
        completeness = 0
        if obj.mobile_profile:
            completeness += 33
        if obj.web_profile:
            completeness += 33
        if obj.desktop_profile:
            completeness += 34
        return min(completeness, 100)