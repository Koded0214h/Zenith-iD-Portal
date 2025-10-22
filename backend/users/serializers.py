from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
import random
import string

from .models import CustomUser, UserProfile, UserSession, OTPVerification

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ('email', 'phone_number', 'password', 'password_confirm', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'required': True},
            'phone_number': {'required': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        if CustomUser.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})
        
        if CustomUser.objects.filter(phone_number=attrs['phone_number']).exists():
            raise serializers.ValidationError({"phone_number": "A user with this phone number already exists."})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(
            username=validated_data['email'],  # Use email as username
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password']
        )
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        # Generate OTP for phone verification
        OTPVerification.objects.create(
            user=user,
            otp_code=''.join(random.choices(string.digits, k=6)),
            purpose='phone_verification',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')
        
        if not (email or phone_number):
            raise serializers.ValidationError("Either email or phone number is required.")
        
        if email:
            user = authenticate(username=email, password=password)
            identifier = email
        else:
            try:
                user_obj = CustomUser.objects.get(phone_number=phone_number)
                user = authenticate(username=user_obj.email, password=password)
                identifier = phone_number
            except CustomUser.DoesNotExist:
                user = None
        
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        
        attrs['user'] = user
        attrs['identifier'] = identifier
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    full_name = serializers.SerializerMethodField()
    age = serializers.ReadOnlyField()
    
    class Meta:
        model = UserProfile
        fields = (
            'email', 'phone_number', 'full_name', 'date_of_birth', 'age',
            'address', 'occupation', 'marital_status', 'gender', 'profile_picture'
        )
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()

class CustomUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'is_verified', 'verification_tier', 'date_joined', 'last_updated', 'profile'
        )
        read_only_fields = ('id', 'date_joined', 'last_updated', 'is_verified')

class OTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    purpose = serializers.ChoiceField(choices=OTPVerification._meta.get_field('purpose').choices)
    
    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        
        if not (email or phone_number):
            raise serializers.ValidationError("Either email or phone number is required.")
        
        try:
            if email:
                user = CustomUser.objects.get(email=email)
            else:
                user = CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        
        attrs['user'] = user
        return attrs

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    otp_code = serializers.CharField(max_length=6)
    purpose = serializers.ChoiceField(choices=OTPVerification._meta.get_field('purpose').choices)
    
    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        otp_code = attrs.get('otp_code')
        purpose = attrs.get('purpose')
        
        if not (email or phone_number):
            raise serializers.ValidationError("Either email or phone number is required.")
        
        try:
            if email:
                user = CustomUser.objects.get(email=email)
            else:
                user = CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        
        try:
            otp = OTPVerification.objects.get(
                user=user,
                otp_code=otp_code,
                purpose=purpose,
                is_used=False
            )
        except OTPVerification.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP code.")
        
        if not otp.is_valid():
            raise serializers.ValidationError("OTP has expired.")
        
        attrs['user'] = user
        attrs['otp_instance'] = otp
        return attrs