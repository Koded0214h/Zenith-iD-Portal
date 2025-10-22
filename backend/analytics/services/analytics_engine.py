from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q
from datetime import timedelta
import logging
from analytics.models import ( 
    OnboardingFunnel, UserBehaviorEvent, BusinessMetrics,
    FunnelConversion, ProductPerformance, RiskAnalytics
)
from users.models import CustomUser 
from accountz.models import BankAccount, Transaction, ProductRecommendation  
from verification.models import IDVerification, FacialVerification  
from biometrics.models import BiometricVerificationLog  

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """Main analytics engine for processing and calculating metrics"""
    
    @staticmethod
    def calculate_onboarding_metrics():
        """Calculate onboarding funnel metrics"""
        try:
            # Get time range for calculation (last 30 days)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            
            # Get all onboarding funnels in period
            funnels = OnboardingFunnel.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            total_users = funnels.count()
            completed_onboarding = funnels.filter(is_completed=True).count()
            avg_time = funnels.filter(is_completed=True).aggregate(
                avg_time=Avg('total_onboarding_duration')
            )['avg_time'] or 0
            
            within_3_minutes = funnels.filter(
                is_completed=True,
                total_onboarding_duration__lte=180
            ).count()
            
            conversion_rate = (completed_onboarding / total_users * 100) if total_users > 0 else 0
            three_minute_success_rate = (within_3_minutes / completed_onboarding * 100) if completed_onboarding > 0 else 0
            
            # Drop-off analysis
            dropoff_points = funnels.filter(is_completed=False).values('dropped_off_at').annotate(
                count=Count('id')
            ).order_by('-count')
            
            return {
                'total_users': total_users,
                'completed_onboarding': completed_onboarding,
                'conversion_rate': round(conversion_rate, 2),
                'average_time_seconds': round(avg_time, 2),
                'three_minute_success_rate': round(three_minute_success_rate, 2),
                'dropoff_analysis': list(dropoff_points),
                'period': f"{start_date.date()} to {end_date.date()}"
            }
            
        except Exception as e:
            logger.error(f"Onboarding metrics calculation failed: {str(e)}")
            return {}
    
    @staticmethod
    def calculate_business_metrics():
        """Calculate key business performance indicators"""
        try:
            today = timezone.now().date()
            yesterday = today - timedelta(days=1)
            
            # User metrics
            total_users = CustomUser.objects.count()
            new_users_today = CustomUser.objects.filter(date_joined__date=today).count()
            active_users_today = CustomUser.objects.filter(
                last_login__date=today
            ).count()
            
            # Account metrics
            total_accounts = BankAccount.objects.filter(status='active').count()
            new_accounts_today = BankAccount.objects.filter(
                created_at__date=today,
                status='active'
            ).count()
            
            # Transaction metrics
            transactions_today = Transaction.objects.filter(
                created_at__date=today,
                status='completed'
            )
            total_volume_today = transactions_today.aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            # Product metrics
            product_conversions = ProductRecommendation.objects.filter(
                is_accepted=True,
                created_at__date=today
            ).count()
            total_recommendations = ProductRecommendation.objects.filter(
                created_at__date=today
            ).count()
            product_conversion_rate = (product_conversions / total_recommendations * 100) if total_recommendations > 0 else 0
            
            return {
                'total_users': total_users,
                'new_users_today': new_users_today,
                'active_users_today': active_users_today,
                'total_accounts': total_accounts,
                'new_accounts_today': new_accounts_today,
                'transactions_today': transactions_today.count(),
                'total_volume_today': float(total_volume_today),
                'product_conversion_rate': round(product_conversion_rate, 2),
                'calculated_at': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Business metrics calculation failed: {str(e)}")
            return {}
    
    @staticmethod
    def calculate_risk_metrics():
        """Calculate risk and security metrics"""
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            
            # Verification fraud attempts
            failed_verifications = IDVerification.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                status='failed'
            ).count()
            
            total_verifications = IDVerification.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).count()
            
            # Biometric anomalies
            biometric_anomalies = BiometricVerificationLog.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                anomaly_detected=True
            ).count()
            
            total_biometric_checks = BiometricVerificationLog.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).count()
            
            # Fraud rates
            verification_fraud_rate = (failed_verifications / total_verifications * 100) if total_verifications > 0 else 0
            biometric_anomaly_rate = (biometric_anomalies / total_biometric_checks * 100) if total_biometric_checks > 0 else 0
            
            return {
                'verification_fraud_rate': round(verification_fraud_rate, 2),
                'biometric_anomaly_rate': round(biometric_anomaly_rate, 2),
                'failed_verifications': failed_verifications,
                'biometric_anomalies': biometric_anomalies,
                'total_checks': total_verifications + total_biometric_checks,
                'period': f"{start_date.date()} to {end_date.date()}"
            }
            
        except Exception as e:
            logger.error(f"Risk metrics calculation failed: {str(e)}")
            return {}
    
    @staticmethod
    def track_user_behavior(user, event_type, event_name, **kwargs):
        """Track user behavior events"""
        try:
            event = UserBehaviorEvent.objects.create(
                user=user,
                event_type=event_type,
                event_name=event_name,
                screen_name=kwargs.get('screen_name', ''),
                element_id=kwargs.get('element_id', ''),
                metadata=kwargs.get('metadata', {}),
                session_id=kwargs.get('session_id', ''),
                ip_address=kwargs.get('ip_address'),
                user_agent=kwargs.get('user_agent', '')
            )
            return event
        except Exception as e:
            logger.error(f"User behavior tracking failed: {str(e)}")
            return None
    
    @staticmethod
    def update_onboarding_funnel(user, step, timestamp=None, **kwargs):  # ← FIXED: Added **kwargs
        """Update user's onboarding funnel progress"""
        try:
            funnel, created = OnboardingFunnel.objects.get_or_create(user=user)
            timestamp = timestamp or timezone.now()
            
            if step == 'registration_completed':
                funnel.registration_completed_at = timestamp
            elif step == 'id_verification_started':
                funnel.id_verification_started_at = timestamp
            elif step == 'id_verification_completed':
                funnel.id_verification_completed_at = timestamp
            elif step == 'facial_verification_started':
                funnel.facial_verification_started_at = timestamp
            elif step == 'facial_verification_completed':
                funnel.facial_verification_completed_at = timestamp
            elif step == 'account_created':
                funnel.account_created_at = timestamp
                funnel.is_completed = True
            elif step == 'first_funding':
                funnel.first_funding_at = timestamp
            elif step == 'dropped_off':
                funnel.dropped_off_at = kwargs.get('dropoff_point', 'unknown')  # ← Now kwargs is defined
            
            funnel.calculate_durations()
            funnel.save()
            
        except Exception as e:
            logger.error(f"Onboarding funnel update failed: {str(e)}")

class ProductAnalytics:
    """Analytics specifically for product performance"""
    
    @staticmethod
    def calculate_product_performance():
        """Calculate performance metrics for all product recommendations"""
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            
            products = ProductRecommendation.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            performance_data = []
            
            for product_type in ['loan', 'savings', 'card_upgrade', 'investment']:
                type_products = products.filter(product_type=product_type)
                
                total_views = UserBehaviorEvent.objects.filter(
                    event_type='product_view',
                    metadata__product_type=product_type,
                    created_at__gte=start_date,
                    created_at__lte=end_date
                ).count()
                
                total_clicks = UserBehaviorEvent.objects.filter(
                    event_type='recommendation_click',
                    metadata__product_type=product_type,
                    created_at__gte=start_date,
                    created_at__lte=end_date
                ).count()
                
                conversions = type_products.filter(is_accepted=True).count()
                
                click_through_rate = (total_clicks / total_views * 100) if total_views > 0 else 0
                conversion_rate = (conversions / total_clicks * 100) if total_clicks > 0 else 0
                
                performance_data.append({
                    'product_type': product_type,
                    'total_recommendations': type_products.count(),
                    'total_views': total_views,
                    'total_clicks': total_clicks,
                    'conversions': conversions,
                    'click_through_rate': round(click_through_rate, 2),
                    'conversion_rate': round(conversion_rate, 2)
                })
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Product performance calculation failed: {str(e)}")
            return []

class FunnelAnalytics:
    """Analytics for funnel conversion optimization"""
    
    @staticmethod
    def analyze_onboarding_funnel(period_days=30):
        """Detailed analysis of onboarding funnel"""
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=period_days)
            
            funnels = OnboardingFunnel.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            # Step-by-step conversion analysis
            steps = [
                ('registration', 'registration_completed_at'),
                ('id_verification_start', 'id_verification_started_at'),
                ('id_verification_complete', 'id_verification_completed_at'),
                ('facial_verification_start', 'facial_verification_started_at'),
                ('facial_verification_complete', 'facial_verification_completed_at'),
                ('account_creation', 'account_created_at'),
                ('first_funding', 'first_funding_at')
            ]
            
            funnel_analysis = []
            previous_count = funnels.count()
            
            for step_name, step_field in steps:
                step_count = funnels.filter(**{f"{step_field}__isnull": False}).count()
                conversion_rate = (step_count / previous_count * 100) if previous_count > 0 else 0
                
                funnel_analysis.append({
                    'step': step_name,
                    'users_reached': step_count,
                    'conversion_rate': round(conversion_rate, 2),
                    'dropoff_rate': round(100 - conversion_rate, 2) if previous_count > 0 else 0
                })
                
                previous_count = step_count
            
            return funnel_analysis
            
        except Exception as e:
            logger.error(f"Funnel analysis failed: {str(e)}")
            return []