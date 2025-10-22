from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Overview
    path('dashboard/', views.AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    
    # Specific Analytics
    path('onboarding/', views.OnboardingAnalyticsView.as_view(), name='onboarding-analytics'),
    path('products/performance/', views.ProductPerformanceView.as_view(), name='product-performance'),
    path('risk/', views.RiskAnalyticsView.as_view(), name='risk-analytics'),
    path('funnel/analysis/', views.FunnelAnalysisView.as_view(), name='funnel-analysis'),
    path('business/metrics/', views.BusinessMetricsView.as_view(), name='business-metrics'),
    
    # User Behavior Tracking
    path('behavior/track/', views.UserBehaviorTrackerView.as_view(), name='track-behavior'),
    path('behavior/analyze/', views.UserBehaviorAnalysisView.as_view(), name='analyze-behavior'),
    
    # Progress Updates
    path('onboarding/progress/', views.update_onboarding_progress, name='update-onboarding-progress'),
]