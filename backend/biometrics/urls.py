from django.urls import path
from . import views

urlpatterns = [
    # Session Management
    path('sessions/start/', views.start_biometric_session, name='start-session'),
    path('sessions/end/<str:session_id>/', views.end_biometric_session, name='end-session'),
    path('sessions/', views.BiometricSessionsView.as_view(), name='user-sessions'),
    
    # Data Collection
    path('data/collect/', views.BiometricDataCollectionView.as_view(), name='collect-data'),
    
    # Verification
    path('verify/', views.BiometricVerificationView.as_view(), name='biometric-verify'),
    path('verification/history/', views.VerificationHistoryView.as_view(), name='verification-history'),
    
    # Profile Management
    path('profile/', views.BiometricProfileView.as_view(), name='biometric-profile'),
    
    # Web-specific endpoints
    path('web/data/collect/', views.WebDataCollectionView.as_view(), name='web-collect-data'),
    
    # Cross-platform endpoints
    path('cross-platform/verify/', views.CrossPlatformVerificationView.as_view(), name='cross-platform-verify'),
    path('cross-platform/profile/', views.CrossPlatformProfileView.as_view(), name='cross-platform-profile'),
]