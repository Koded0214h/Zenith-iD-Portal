from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction as db_transaction
from datetime import timezone
import logging

from .models import BankAccount, VirtualCard, Transaction, FundingMethod, ProductRecommendation, USSDSession
from .serializers import (
    BankAccountSerializer, VirtualCardSerializer, TransactionSerializer,
    FundingMethodSerializer, ProductRecommendationSerializer, USSDSessionSerializer,
    AccountCreationSerializer, FundAccountSerializer, TransferSerializer
)
from .services.account_service import AccountService, ProductRecommendationService

logger = logging.getLogger(__name__)

class AccountCreationView(APIView):
    """Create a new bank account for verified user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = AccountCreationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                with db_transaction.atomic():
                    # Create account and virtual card
                    account, card = AccountService.create_user_account(
                        user=request.user,
                        account_type=serializer.validated_data['account_type']
                    )
                    
                    # Generate initial product recommendations
                    ProductRecommendationService.generate_recommendations(request.user)
                    
                    return Response({
                        'status': 'success',
                        'message': 'Account created successfully',
                        'account': BankAccountSerializer(account).data,
                        'virtual_card': VirtualCardSerializer(card).data
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                logger.error(f"Account creation failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Account creation failed'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class AccountListView(generics.ListAPIView):
    """Get user's bank accounts"""
    serializer_class = BankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

class AccountDetailView(generics.RetrieveAPIView):
    """Get specific account details"""
    serializer_class = BankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

class VirtualCardsView(generics.ListAPIView):
    """Get user's virtual cards"""
    serializer_class = VirtualCardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return VirtualCard.objects.filter(account__user=self.request.user)

class FundAccountView(APIView):
    """Fund user account"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = FundAccountSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Get user's active account
                account = BankAccount.objects.filter(user=request.user, status='active').first()
                if not account:
                    return Response({
                        'status': 'error',
                        'message': 'No active account found'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Process funding based on method
                method = serializer.validated_data['method']
                amount = serializer.validated_data['amount']
                
                if method == 'ussd':
                    # Create USSD session
                    ussd_session = USSDSession.objects.create(
                        user=request.user,
                        account=account,
                        amount=amount,
                        ussd_code=serializer.validated_data.get('ussd_code', '*966#'),
                        bank_name=serializer.validated_data.get('bank_name', 'Zenith Bank'),
                        session_id=f"USSD_{request.user.id}_{int(timezone.now().timestamp())}"
                    )
                    
                    return Response({
                        'status': 'success',
                        'message': 'USSD session created',
                        'ussd_session': USSDSessionSerializer(ussd_session).data,
                        'instructions': f"Dial {ussd_session.ussd_code} to complete transaction"
                    })
                
                else:
                    # Process direct funding
                    transaction = AccountService.fund_account(
                        account=account,
                        amount=amount,
                        method=method
                    )
                    
                    return Response({
                        'status': 'success',
                        'message': 'Account funded successfully',
                        'transaction': TransactionSerializer(transaction).data,
                        'new_balance': account.balance
                    })
                    
            except Exception as e:
                logger.error(f"Account funding failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Funding failed'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class TransferView(APIView):
    """Process bank transfers"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = TransferSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                # Get user's active account
                from_account = BankAccount.objects.filter(user=request.user, status='active').first()
                if not from_account:
                    return Response({
                        'status': 'error',
                        'message': 'No active account found'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Process transfer
                transaction = AccountService.process_transfer(
                    from_account=from_account,
                    to_account_number=serializer.validated_data['beneficiary_account'],
                    amount=serializer.validated_data['amount'],
                    narration=serializer.validated_data['narration']
                )
                
                return Response({
                    'status': 'success',
                    'message': 'Transfer completed successfully',
                    'transaction': TransactionSerializer(transaction).data,
                    'new_balance': from_account.balance
                })
                
            except ValueError as e:
                return Response({
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
                
            except Exception as e:
                logger.error(f"Transfer failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Transfer failed'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class TransactionHistoryView(generics.ListAPIView):
    """Get user's transaction history"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Transaction.objects.filter(account__user=self.request.user).order_by('-created_at')

class ProductRecommendationsView(generics.ListAPIView):
    """Get user's product recommendations"""
    serializer_class = ProductRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ProductRecommendation.objects.filter(user=self.request.user, is_expired=False)

class AcceptProductRecommendationView(APIView):
    """Accept a product recommendation"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, recommendation_id):
        try:
            recommendation = ProductRecommendation.objects.get(
                id=recommendation_id,
                user=request.user,
                is_expired=False
            )
            
            if not recommendation.is_eligible():
                return Response({
                    'status': 'error',
                    'message': 'This recommendation is no longer eligible'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark as accepted
            recommendation.is_accepted = True
            recommendation.save()
            
            # TODO: Process the product acceptance (create loan account, etc.)
            
            return Response({
                'status': 'success',
                'message': f'{recommendation.product_type} accepted successfully'
            })
            
        except ProductRecommendation.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Recommendation not found'
            }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def account_dashboard(request):
    """Get user's account dashboard data"""
    try:
        accounts = BankAccount.objects.filter(user=request.user, status='active')
        cards = VirtualCard.objects.filter(account__user=request.user, status='active')
        recent_transactions = Transaction.objects.filter(
            account__user=request.user
        ).order_by('-created_at')[:5]
        recommendations = ProductRecommendation.objects.filter(
            user=request.user, is_expired=False
        )[:3]
        
        dashboard_data = {
            'accounts': BankAccountSerializer(accounts, many=True).data,
            'virtual_cards': VirtualCardSerializer(cards, many=True).data,
            'recent_transactions': TransactionSerializer(recent_transactions, many=True).data,
            'product_recommendations': ProductRecommendationSerializer(recommendations, many=True).data,
            'total_balance': sum(account.balance for account in accounts)
        }
        
        return Response({
            'status': 'success',
            'data': dashboard_data
        })
        
    except Exception as e:
        logger.error(f"Dashboard data fetch failed: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Failed to load dashboard data'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)