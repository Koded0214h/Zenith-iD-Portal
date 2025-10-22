from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
import logging, json

from .models import (
    BehavioralBiometrics, BiometricSession, 
    BiometricProfile, BiometricVerificationLog,
    WebBehavioralData, CrossPlatformProfile
)
from .serializers import (
    BehavioralBiometricsSerializer, BiometricSessionSerializer,
    BiometricProfileSerializer, BiometricVerificationLogSerializer,
    BiometricDataCollectionSerializer, BiometricVerificationRequestSerializer,
    VerificationResultSerializer, WebBehavioralDataSerializer, WebDataCollectionSerializer,
    CrossPlatformProfileSerializer
)
from .services.behavioral_analyzer import BehavioralAnalyzer
from .services.web_behavior_analyzer import WebBehaviorAnalyzer

logger = logging.getLogger(__name__)

class BiometricDataCollectionView(APIView):
    """
    Endpoint for mobile app to send behavioral biometric data
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = BiometricDataCollectionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = request.user
                session_id = serializer.validated_data['session_id']
                
                # Get or create session
                session, created = BiometricSession.objects.get_or_create(
                    session_id=session_id,
                    user=user,
                    defaults={
                        'session_type': 'continuous',
                        'ip_address': self._get_client_ip(request),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')
                    }
                )
                
                # Prepare biometric data
                biometric_data = {
                    'typing_pattern': {
                        'key_hold_times': serializer.validated_data.get('key_hold_times', []),
                        'flight_times': serializer.validated_data.get('flight_times', []),
                    },
                    'touch_patterns': {
                        'swipe_speeds': [s.get('speed', 0) for s in serializer.validated_data.get('swipe_data', [])],
                        'touch_pressures': [t.get('pressure', 0) for t in serializer.validated_data.get('touch_data', [])],
                    },
                    'device_characteristics': {
                        'device_id': serializer.validated_data.get('device_info', {}).get('device_id', ''),
                        'os': serializer.validated_data.get('device_info', {}).get('os', ''),
                        'screen_size': serializer.validated_data.get('device_info', {}).get('screen_size', ''),
                        'sensors': serializer.validated_data.get('sensor_data', []),
                    }
                }
                
                # Create behavioral signature
                analyzer = BehavioralAnalyzer()
                biometric_signature = analyzer.create_biometric_signature(biometric_data)
                
                # Save biometric record
                biometric_record = BehavioralBiometrics.objects.create(
                    user=user,
                    session_id=session_id,
                    typing_pattern=biometric_data['typing_pattern'],
                    touch_patterns=biometric_data['touch_patterns'],
                    device_characteristics=biometric_data['device_characteristics'],
                    biometric_signature=biometric_signature,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Calculate and update confidence score
                biometric_record.calculate_confidence()
                biometric_record.save()
                
                # Update session metrics
                session.data_points_collected += 1
                session.save()
                
                # Update user's biometric profile
                self._update_user_profile(user, biometric_data)
                
                return Response({
                    'status': 'success',
                    'message': 'Biometric data collected successfully',
                    'record_id': biometric_record.id,
                    'confidence_score': biometric_record.confidence_score
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Biometric data collection failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Failed to process biometric data'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _update_user_profile(self, user, biometric_data):
        """Update user's biometric profile with new data"""
        try:
            profile, created = BiometricProfile.objects.get_or_create(user=user)
            analyzer = BehavioralAnalyzer()
            
            # Update profile with new sample (simplified)
            profile.samples_collected += 1
            profile.last_updated = timezone.now()
            profile.save()
            
        except Exception as e:
            logger.error(f"Profile update failed: {str(e)}")

class BiometricVerificationView(APIView):
    """
    Endpoint for biometric verification during authentication/transactions
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = BiometricVerificationRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = request.user
                session_id = serializer.validated_data['session_id']
                verification_type = serializer.validated_data['verification_type']
                
                # Get user's biometric profile
                try:
                    profile = BiometricProfile.objects.get(user=user)
                    profile_data = BiometricProfileSerializer(profile).data
                except BiometricProfile.DoesNotExist:
                    return Response({
                        'status': 'error',
                        'message': 'No biometric profile found. Please complete enrollment first.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Analyze current biometric sample
                analyzer = BehavioralAnalyzer()
                is_match, confidence, risk_score = analyzer.verify_behavioral_match(
                    serializer.validated_data['biometric_sample'],
                    profile_data
                )
                
                # Determine verification status
                if is_match and confidence >= 0.7:
                    status_str = 'success'
                    message = 'Biometric verification successful'
                elif confidence >= 0.5:
                    status_str = 'suspicious'
                    message = 'Biometric verification suspicious - additional authentication required'
                else:
                    status_str = 'failed'
                    message = 'Biometric verification failed'
                
                # Log verification attempt
                verification_log = BiometricVerificationLog.objects.create(
                    user=user,
                    verification_type=verification_type,
                    status=status_str,
                    confidence_score=confidence,
                    risk_score=risk_score,
                    anomaly_detected=risk_score > 0.7,
                    biometric_data=serializer.validated_data['biometric_sample'],
                    device_fingerprint=serializer.validated_data['device_fingerprint'],
                    ip_address=serializer.validated_data['ip_address']
                )
                
                # Prepare response
                result_data = {
                    'is_verified': is_match and confidence >= 0.7,
                    'confidence_score': confidence,
                    'risk_score': risk_score,
                    'status': status_str,
                    'message': message,
                    'requires_challenge': status_str == 'suspicious',
                    'challenge_type': 'otp' if status_str == 'suspicious' else None
                }
                
                return Response({
                    'status': 'success',
                    'verification_id': verification_log.id,
                    'result': VerificationResultSerializer(result_data).data
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Biometric verification failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Verification processing failed'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class BiometricProfileView(generics.RetrieveAPIView):
    """Get user's biometric profile"""
    serializer_class = BiometricProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        profile, created = BiometricProfile.objects.get_or_create(user=self.request.user)
        return profile

class BiometricSessionsView(generics.ListAPIView):
    """Get user's biometric sessions"""
    serializer_class = BiometricSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return BiometricSession.objects.filter(user=self.request.user).order_by('-start_time')

class VerificationHistoryView(generics.ListAPIView):
    """Get user's verification history"""
    serializer_class = BiometricVerificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return BiometricVerificationLog.objects.filter(user=self.request.user).order_by('-created_at')

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_biometric_session(request):
    """Start a new biometric session"""
    try:
        session_type = request.data.get('session_type', 'continuous')
        
        session = BiometricSession.objects.create(
            user=request.user,
            session_type=session_type,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'status': 'success',
            'session_id': session.session_id,
            'message': f'{session_type} session started'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Session start failed: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Failed to start session'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def end_biometric_session(request, session_id):
    """End a biometric session"""
    try:
        session = BiometricSession.objects.get(
            session_id=session_id,
            user=request.user
        )
        
        session.end_time = timezone.now()
        session.is_active = False
        session.save()
        
        return Response({
            'status': 'success',
            'message': 'Session ended successfully'
        }, status=status.HTTP_200_OK)
        
    except BiometricSession.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Session not found'
        }, status=status.HTTP_404_NOT_FOUND)

def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class WebDataCollectionView(APIView):
    """
    Endpoint for web applications to send behavioral data
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = WebDataCollectionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = request.user
                session_id = serializer.validated_data['session_id']
                
                # Get or create web session
                session, created = BiometricSession.objects.get_or_create(
                    session_id=session_id,
                    user=user,
                    defaults={
                        'session_type': 'continuous',
                        'ip_address': self._get_client_ip(request),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')
                    }
                )
                
                # Prepare web behavioral data
                web_data = {
                    'mouse_movements': serializer.validated_data.get('mouse_movements', []),
                    'scroll_events': serializer.validated_data.get('scroll_events', []),
                    'keystroke_timing': serializer.validated_data.get('keystroke_timing', []),
                    'form_interactions': serializer.validated_data.get('form_interactions', []),
                    'page_events': serializer.validated_data.get('page_events', []),
                    'browser_info': serializer.validated_data.get('browser_info', {}),
                    'screen_info': serializer.validated_data.get('screen_info', {})
                }
                
                # Create web behavioral signature
                web_analyzer = WebBehaviorAnalyzer()
                behavioral_signature = web_analyzer.create_web_behavioral_signature(web_data)
                
                # Save web behavioral record
                web_record = WebBehavioralData.objects.create(
                    user=user,
                    session_id=session_id,
                    mouse_movements=web_data['mouse_movements'],
                    scroll_behavior=web_data['scroll_events'],
                    form_filling_patterns=web_data['form_interactions'],
                    browser_events=web_data['page_events'],
                    timing_patterns=web_data['keystroke_timing'],
                    screen_resolution=f"{web_data['screen_info'].get('width', 0)}x{web_data['screen_info'].get('height', 0)}",
                    browser_type=web_data['browser_info'].get('userAgent', '')[:50],
                    plugins=web_data['browser_info'].get('plugins', [])
                )
                
                # Also create a cross-platform biometric record
                biometric_record = BehavioralBiometrics.objects.create(
                    user=user,
                    session_id=session_id,
                    platform='web',
                    typing_pattern={'flight_times': [kt.get('next_key_delay', 0) for kt in web_data['keystroke_timing']]},
                    touch_patterns={},  # No touch data on web
                    device_characteristics={
                        'device_id': f"web_{web_data['browser_info'].get('userAgent', '')}",
                        'os': web_data['browser_info'].get('platform', ''),
                        'screen_size': f"{web_data['screen_info'].get('width', 0)}x{web_data['screen_info'].get('height', 0)}"
                    },
                    biometric_signature=behavioral_signature,
                    browser_fingerprint=json.dumps(web_data['browser_info']),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Calculate confidence
                biometric_record.calculate_confidence()
                biometric_record.save()
                
                # Update cross-platform profile
                self._update_cross_platform_profile(user, web_data, 'web')
                
                return Response({
                    'status': 'success',
                    'message': 'Web behavioral data collected successfully',
                    'record_id': web_record.id,
                    'platform': 'web'
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Web data collection failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Failed to process web behavioral data'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def _update_cross_platform_profile(self, user, web_data, platform):
        """Update cross-platform profile with web data"""
        try:
            profile, created = CrossPlatformProfile.objects.get_or_create(user=user)
            
            # Update web-specific profile
            web_analyzer = WebBehaviorAnalyzer()
            web_features = {
                'mouse_patterns': web_analyzer._extract_mouse_features(web_data.get('mouse_movements', [])),
                'typing_rhythm': web_analyzer._extract_web_typing_features(web_data.get('keystroke_timing', [])),
                'scroll_patterns': web_analyzer._extract_scroll_features(web_data.get('scroll_events', [])),
                'browser_fingerprint': web_analyzer._create_browser_fingerprint(web_data.get('browser_info', {}))
            }
            
            profile.web_profile = web_features
            
            # Update preferred platforms
            if platform not in profile.preferred_platforms:
                profile.preferred_platforms.append(platform)
            
            profile.save()
            
        except Exception as e:
            logger.error(f"Cross-platform profile update failed: {str(e)}")

class CrossPlatformVerificationView(APIView):
    """
    Unified verification that works across all platforms
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        platform = request.data.get('platform', 'web')  # web, mobile, desktop
        verification_type = request.data.get('verification_type', 'login')
        
        try:
            user = request.user
            
            # Get cross-platform profile
            try:
                cross_profile = CrossPlatformProfile.objects.get(user=user)
                profile_data = CrossPlatformProfileSerializer(cross_profile).data
            except CrossPlatformProfile.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'No cross-platform profile found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Platform-specific verification
            if platform == 'web':
                result = self._verify_web_behavior(request.data, profile_data)
            elif platform == 'mobile':
                result = self._verify_mobile_behavior(request.data, profile_data)
            else:
                return Response({
                    'status': 'error',
                    'message': f'Unsupported platform: {platform}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Log verification attempt
            verification_log = BiometricVerificationLog.objects.create(
                user=user,
                verification_type=verification_type,
                status=result['status'],
                confidence_score=result['confidence_score'],
                risk_score=result['risk_score'],
                anomaly_detected=result['risk_score'] > 0.7,
                biometric_data=request.data.get('biometric_sample', {}),
                device_fingerprint=request.data.get('device_fingerprint', ''),
                ip_address=self._get_client_ip(request)
            )
            
            return Response({
                'status': 'success',
                'verification_id': verification_log.id,
                'platform': platform,
                'result': VerificationResultSerializer(result).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Cross-platform verification failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Verification processing failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _verify_web_behavior(self, request_data, profile_data):
        """Verify web behavioral data"""
        web_analyzer = WebBehaviorAnalyzer()
        is_match, confidence, risk_score = web_analyzer.verify_web_behavior(
            request_data.get('biometric_sample', {}),
            profile_data.get('web_profile', {})
        )
        
        return self._prepare_verification_result(is_match, confidence, risk_score)
    
    def _verify_mobile_behavior(self, request_data, profile_data):
        """Verify mobile behavioral data"""
        analyzer = BehavioralAnalyzer()
        is_match, confidence, risk_score = analyzer.verify_behavioral_match(
            request_data.get('biometric_sample', {}),
            profile_data.get('mobile_profile', {})
        )
        
        return self._prepare_verification_result(is_match, confidence, risk_score)
    
    def _prepare_verification_result(self, is_match, confidence, risk_score):
        """Prepare standardized verification result"""
        if is_match and confidence >= 0.7:
            status_str = 'success'
            message = 'Biometric verification successful'
        elif confidence >= 0.5:
            status_str = 'suspicious'
            message = 'Verification suspicious - additional authentication required'
        else:
            status_str = 'failed'
            message = 'Biometric verification failed'
        
        return {
            'is_verified': is_match and confidence >= 0.7,
            'confidence_score': confidence,
            'risk_score': risk_score,
            'status': status_str,
            'message': message,
            'requires_challenge': status_str == 'suspicious',
            'challenge_type': 'otp' if status_str == 'suspicious' else None
        }
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip