from django.urls import path
from . import views

urlpatterns = [
    # ID Verification
    path('id-verification/', views.IDVerificationView.as_view(), name='id-verification'),
    path('id-verification/status/<int:verification_id>/', views.VerificationStatusView.as_view(), name='verification-status'),
    path('id-verification/history/', views.UserVerificationsView.as_view(), name='verification-history'),
    path('id-verification/bulk-status/', views.bulk_verification_status, name='bulk-verification-status'),
    
    # Facial Verification
    path('facial-verification/', views.FacialVerificationView.as_view(), name='facial-verification'),
    
    # Webhooks (for external services)
    path('webhook/<str:verification_type>/', views.VerificationWebhookView.as_view(), name='verification-webhook'),
]