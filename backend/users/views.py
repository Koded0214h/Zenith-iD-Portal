from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
import random
import string

from .models import CustomUser, UserProfile, UserSession, OTPVerification
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, CustomUserSerializer,
    UserProfileSerializer, OTPSerializer, OTPVerificationSerializer
)

class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'status': 'success',
                'message': 'User registered successfully. Please verify your phone number.',
                'user': CustomUserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Create user session
            session = UserSession.objects.create(
                user=user,
                session_key=request.session.session_key or 'mobile_session',
                device_info=request.META.get('HTTP_USER_AGENT', ''),
                ip_address=self.get_client_ip(request)
            )
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'status': 'success',
                'message': 'Login successful',
                'user': CustomUserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'session_id': session.id
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user.profile

class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            purpose = serializer.validated_data['purpose']
            
            # Invalidate previous OTPs for same purpose
            OTPVerification.objects.filter(
                user=user, 
                purpose=purpose, 
                is_used=False
            ).update(is_used=True)
            
            # Generate new OTP
            otp_code = ''.join(random.choices(string.digits, k=6))
            otp = OTPVerification.objects.create(
                user=user,
                otp_code=otp_code,
                purpose=purpose,
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            
            # TODO: Integrate with SMS service (Twilio, etc.)
            print(f"OTP for {user.email}: {otp_code}")  # Remove in production
            
            return Response({
                'status': 'success',
                'message': f'OTP sent successfully for {purpose}',
                'purpose': purpose
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            otp_instance = serializer.validated_data['otp_instance']
            purpose = serializer.validated_data['purpose']
            
            # Mark OTP as used
            otp_instance.is_used = True
            otp_instance.save()
            
            # Handle different purposes
            if purpose == 'phone_verification':
                user.is_verified = True
                user.verification_tier = 2  # Basic verification complete
                user.save()
            
            return Response({
                'status': 'success',
                'message': f'{purpose.replace("_", " ").title()} verified successfully',
                'user': CustomUserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class UserLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Get session ID from request
            session_id = request.data.get('session_id')
            if session_id:
                try:
                    session = UserSession.objects.get(id=session_id, user=request.user)
                    session.logout_time = timezone.now()
                    session.is_active = False
                    session.save()
                except UserSession.DoesNotExist:
                    pass
            
            # Blacklist refresh token
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'status': 'success',
                'message': 'Logged out successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard(request):
    """Get user dashboard data"""
    user = request.user
    active_sessions = UserSession.objects.filter(user=user, is_active=True).count()
    
    dashboard_data = {
        'user': CustomUserSerializer(user).data,
        'stats': {
            'active_sessions': active_sessions,
            'verification_tier': user.verification_tier,
            'account_age_days': (timezone.now() - user.date_joined).days
        }
    }
    
    return Response({
        'status': 'success',
        'data': dashboard_data
    }, status=status.HTTP_200_OK)