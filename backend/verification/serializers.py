from rest_framework import serializers
from django.utils import timezone

from .models import IDVerification, FacialVerification, GovernmentVerificationLog, VerificationSettings

class IDVerificationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    processing_time = serializers.SerializerMethodField()
    
    class Meta:
        model = IDVerification
        fields = (
            'id', 'user', 'user_email', 'user_phone', 'id_type', 'id_number',
            'id_image_front', 'id_image_back', 'extracted_data', 'ocr_confidence',
            'government_verified', 'verification_score', 'status', 'failure_reason',
            'created_at', 'processed_at', 'completed_at', 'processing_time'
        )
        read_only_fields = (
            'id', 'user', 'extracted_data', 'ocr_confidence', 'government_verified',
            'verification_score', 'status', 'failure_reason', 'processed_at', 
            'completed_at', 'created_at'
        )
    
    def get_processing_time(self, obj):
        if obj.processed_at and obj.created_at:
            return (obj.processed_at - obj.created_at).total_seconds()
        return None
    
    def validate_id_image_front(self, value):
        """Validate ID front image"""
        if value.size > 5 * 1024 * 1024:  # 5MB limit
            raise serializers.ValidationError("Image size cannot exceed 5MB")
        
        allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
        extension = value.name.split('.')[-1].lower()
        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            )
        
        return value

class FacialVerificationSerializer(serializers.ModelSerializer):
    id_verification_type = serializers.CharField(source='id_verification.id_type', read_only=True)
    overall_score = serializers.SerializerMethodField()
    
    class Meta:
        model = FacialVerification
        fields = (
            'id', 'user', 'id_verification', 'id_verification_type',
            'facial_image', 'liveness_score', 'match_score', 
            'liveness_passed', 'match_passed', 'status', 'overall_score',
            'processing_time', 'created_at', 'processed_at'
        )
        read_only_fields = (
            'id', 'user', 'liveness_score', 'match_score', 'liveness_passed',
            'match_passed', 'status', 'processing_time', 'processed_at', 'created_at'
        )
    
    def get_overall_score(self, obj):
        return obj.calculate_overall_score()

class GovernmentVerificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernmentVerificationLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class VerificationRequestSerializer(serializers.Serializer):
    id_type = serializers.ChoiceField(choices=IDVerification.ID_TYPE_CHOICES)
    id_image_front = serializers.ImageField()
    id_image_back = serializers.ImageField(required=False, allow_null=True)
    
    def validate(self, attrs):
        id_type = attrs.get('id_type')
        id_image_back = attrs.get('id_image_back')
        
        # Require back image for certain ID types
        if id_type in ['drivers_license', 'voters_card'] and not id_image_back:
            raise serializers.ValidationError(
                f"Back image is required for {id_type}"
            )
        
        return attrs

class FacialVerificationRequestSerializer(serializers.Serializer):
    id_verification_id = serializers.IntegerField()
    facial_image = serializers.ImageField()
    
    def validate_id_verification_id(self, value):
        """Validate that ID verification exists and is verified"""
        try:
            id_verification = IDVerification.objects.get(id=value)
            if id_verification.status != 'verified':
                raise serializers.ValidationError(
                    "ID verification must be completed before facial verification"
                )
        except IDVerification.DoesNotExist:
            raise serializers.ValidationError("ID verification not found")
        
        return value

class VerificationResultSerializer(serializers.Serializer):
    verification_id = serializers.IntegerField()
    status = serializers.CharField()
    overall_score = serializers.FloatField()
    is_verified = serializers.BooleanField()
    next_steps = serializers.ListField(child=serializers.CharField())
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Add human-readable messages
        if data['is_verified']:
            data['message'] = "Verification completed successfully"
        else:
            data['message'] = "Verification failed. Please try again or contact support."
        
        return data