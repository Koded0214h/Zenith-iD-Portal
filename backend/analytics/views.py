from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
import logging

from .models import (
    OnboardingFunnel, UserBehaviorEvent, ProductPerformance,
    RiskAnalytics, BusinessMetrics, FunnelConversion, UserSegment
)
from .serializers import (
    OnboardingFunnelSerializer, UserBehaviorEventSerializer,
    ProductPerformanceSerializer, RiskAnalyticsSerializer,
    BusinessMetricsSerializer, FunnelConversionSerializer,
    UserSegmentSerializer, AnalyticsDashboardSerializer,
    FunnelAnalysisRequestSerializer, UserBehaviorAnalysisRequestSerializer
)
from .services.analytics_engine import AnalyticsEngine, ProductAnalytics, FunnelAnalytics

logger = logging.getLogger(__name__)

class AnalyticsDashboardView(APIView):
    """Get comprehensive analytics dashboard data"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            # Calculate all metrics
            onboarding_metrics = AnalyticsEngine.calculate_onboarding_metrics()
            business_metrics = AnalyticsEngine.calculate_business_metrics()
            risk_metrics = AnalyticsEngine.calculate_risk_metrics()
            
            dashboard_data = {
                'total_users': business_metrics.get('total_users', 0),
                'active_users_today': business_metrics.get('active_users_today', 0),
                'onboarding_conversion_rate': onboarding_metrics.get('conversion_rate', 0),
                'average_onboarding_time': onboarding_metrics.get('average_time_seconds', 0),
                'total_transactions_today': business_metrics.get('transactions_today', 0),
                'total_volume_today': business_metrics.get('total_volume_today', 0),
                'fraud_prevention_rate': 100 - risk_metrics.get('verification_fraud_rate', 0),
                'product_recommendation_conversion': business_metrics.get('product_conversion_rate', 0),
                
                # Simplified trends (would be calculated from historical data)
                'user_growth_trend': 'up',
                'revenue_growth_trend': 'up',
                'risk_trend': 'stable'
            }
            
            serializer = AnalyticsDashboardSerializer(dashboard_data)
            
            return Response({
                'status': 'success',
                'data': serializer.data,
                'last_updated': timezone.now()
            })
            
        except Exception as e:
            logger.error(f"Dashboard data fetch failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to load analytics dashboard'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OnboardingAnalyticsView(APIView):
    """Get detailed onboarding analytics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            metrics = AnalyticsEngine.calculate_onboarding_metrics()
            
            return Response({
                'status': 'success',
                'data': metrics
            })
            
        except Exception as e:
            logger.error(f"Onboarding analytics fetch failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to load onboarding analytics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProductPerformanceView(APIView):
    """Get product performance analytics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            performance_data = ProductAnalytics.calculate_product_performance()
            
            return Response({
                'status': 'success',
                'data': performance_data
            })
            
        except Exception as e:
            logger.error(f"Product performance fetch failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to load product performance data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RiskAnalyticsView(APIView):
    """Get risk and security analytics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            risk_data = AnalyticsEngine.calculate_risk_metrics()
            
            return Response({
                'status': 'success',
                'data': risk_data
            })
            
        except Exception as e:
            logger.error(f"Risk analytics fetch failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to load risk analytics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FunnelAnalysisView(APIView):
    """Get detailed funnel analysis"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = FunnelAnalysisRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                funnel_type = serializer.validated_data['funnel_type']
                period_days = serializer.validated_data['period_days']
                
                if funnel_type == 'onboarding':
                    analysis_data = FunnelAnalytics.analyze_onboarding_funnel(period_days)
                else:
                    # Other funnel types would be implemented similarly
                    analysis_data = []
                
                return Response({
                    'status': 'success',
                    'funnel_type': funnel_type,
                    'period_days': period_days,
                    'data': analysis_data
                })
                
            except Exception as e:
                logger.error(f"Funnel analysis failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Funnel analysis failed'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class UserBehaviorTrackerView(APIView):
    """Endpoint for tracking user behavior events"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            event_type = request.data.get('event_type')
            event_name = request.data.get('event_name')
            
            if not event_type or not event_name:
                return Response({
                    'status': 'error',
                    'message': 'event_type and event_name are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Track the event
            event = AnalyticsEngine.track_user_behavior(
                user=request.user,
                event_type=event_type,
                event_name=event_name,
                screen_name=request.data.get('screen_name'),
                element_id=request.data.get('element_id'),
                metadata=request.data.get('metadata', {}),
                session_id=request.data.get('session_id'),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            if event:
                return Response({
                    'status': 'success',
                    'message': 'Event tracked successfully',
                    'event_id': event.id
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to track event'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"User behavior tracking failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Event tracking failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserBehaviorAnalysisView(APIView):
    """Analyze user behavior patterns"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = UserBehaviorAnalysisRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user_id = serializer.validated_data.get('user_id')
                event_types = serializer.validated_data.get('event_types', [])
                date_from = serializer.validated_data.get('date_from')
                date_to = serializer.validated_data.get('date_to')
                
                # Build query
                query = UserBehaviorEvent.objects.all()
                
                if user_id:
                    query = query.filter(user_id=user_id)
                else:
                    query = query.filter(user=request.user)
                
                if event_types:
                    query = query.filter(event_type__in=event_types)
                
                if date_from:
                    query = query.filter(created_at__date__gte=date_from)
                
                if date_to:
                    query = query.filter(created_at__date__lte=date_to)
                
                events = query.order_by('-created_at')[:100]  # Limit to recent 100 events
                
                serializer = UserBehaviorEventSerializer(events, many=True)
                
                return Response({
                    'status': 'success',
                    'total_events': events.count(),
                    'events': serializer.data
                })
                
            except Exception as e:
                logger.error(f"User behavior analysis failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Behavior analysis failed'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_onboarding_progress(request):
    """Update user's onboarding funnel progress"""
    try:
        step = request.data.get('step')
        if not step:
            return Response({
                'status': 'error',
                'message': 'Step is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        AnalyticsEngine.update_onboarding_funnel(
            user=request.user,
            step=step,
            timestamp=timezone.now()
        )
        
        return Response({
            'status': 'success',
            'message': f'Onboarding progress updated for step: {step}'
        })
        
    except Exception as e:
        logger.error(f"Onboarding progress update failed: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Failed to update onboarding progress'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BusinessMetricsView(generics.ListAPIView):
    """Get historical business metrics"""
    serializer_class = BusinessMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        metric_type = self.request.query_params.get('metric_type')
        period = self.request.query_params.get('period', 'daily')
        limit = int(self.request.query_params.get('limit', 30))
        
        queryset = BusinessMetrics.objects.all().order_by('-period_date')
        
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)
        
        if period:
            queryset = queryset.filter(period=period)
        
        return queryset[:limit]