from django.urls import path
from . import views

urlpatterns = [
    # Account Management
    path('accounts/create/', views.AccountCreationView.as_view(), name='create-account'),
    path('accounts/', views.AccountListView.as_view(), name='user-accounts'),
    path('accounts/<int:pk>/', views.AccountDetailView.as_view(), name='account-detail'),
    path('accounts/dashboard/', views.account_dashboard, name='account-dashboard'),
    
    # Cards
    path('cards/', views.VirtualCardsView.as_view(), name='virtual-cards'),
    
    # Transactions
    path('fund/', views.FundAccountView.as_view(), name='fund-account'),
    path('transfer/', views.TransferView.as_view(), name='bank-transfer'),
    path('transactions/', views.TransactionHistoryView.as_view(), name='transaction-history'),
    
    # Product Recommendations
    path('recommendations/', views.ProductRecommendationsView.as_view(), name='product-recommendations'),
    path('recommendations/<int:recommendation_id>/accept/', views.AcceptProductRecommendationView.as_view(), name='accept-recommendation'),
]