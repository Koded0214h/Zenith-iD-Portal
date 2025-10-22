from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from django.utils import timezone
import json
import logging

from .tasks import process_facial_verification

from .models import IDVerification, FacialVerification, GovernmentVerificationLog
from .serializers import (
    IDVerificationSerializer, FacialVerificationSerializer,
    VerificationRequestSerializer, FacialVerificationRequestSerializer,
    VerificationResultSerializer
)

from .services.facial_service_simple import SimpleFacialService
from .services.gov_api_service import GovernmentAPIService

logger = logging.getLogger(__name__)

class IDVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = VerificationRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Save uploaded files
                id_image_front = request.FILES['id_image_front']
                id_image_back = request.FILES.get('id_image_back')
                
                front_path = default_storage.save(f'id_documents/front/{id_image_front.name}', id_image_front)
                back_path = None
                if id_image_back:
                    back_path = default_storage.save(f'id_documents/back/{id_image_back.name}', id_image_back)
                
                # Create verification record
                verification = IDVerification.objects.create(
                    user=request.user,
                    id_type=serializer.validated_data['id_type'],
                    id_image_front=front_path,
                    id_image_back=back_path,
                    status='pending'
                )
                
                # Process verification asynchronously (you can use Celery here)
                self._process_verification_async(verification.id)
                
                return Response({
                    'status': 'success',
                    'message': 'ID verification submitted successfully',
                    'verification_id': verification.id,
                    'estimated_completion': '30 seconds'
                }, status=status.HTTP_202_ACCEPTED)
                
            except Exception as e:
                logger.error(f"ID verification submission failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Failed to process verification request'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def _process_verification_async(self, verification_id):
        """Process verification asynchronously"""
        # TODO: Replace with Celery task
        from .tasks import process_id_verification
        process_id_verification.delay(verification_id)

class FacialVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = FacialVerificationRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                id_verification_id = serializer.validated_data['id_verification_id']
                facial_image = request.FILES['facial_image']
                
                # Get ID verification
                id_verification = IDVerification.objects.get(
                    id=id_verification_id,
                    user=request.user
                )
                
                # Save facial image
                facial_path = default_storage.save(f'facial_scans/{facial_image.name}', facial_image)
                
                # Create facial verification record
                facial_verification = FacialVerification.objects.create(
                    user=request.user,
                    id_verification=id_verification,
                    facial_image=facial_path,
                    status='pending'
                )
                
                # Process facial verification
                self._process_facial_verification(facial_verification.id)
                
                return Response({
                    'status': 'success',
                    'message': 'Facial verification submitted successfully',
                    'facial_verification_id': facial_verification.id
                }, status=status.HTTP_202_ACCEPTED)
                
            except IDVerification.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'ID verification not found'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"Facial verification submission failed: {str(e)}")
                return Response({
                    'status': 'error',
                    'message': 'Failed to process facial verification'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Replace the facial service import
from .services.facial_service_simple import SimpleFacialService

# Update the facial verification method
def _process_facial_verification(self, facial_verification_id):
    """Process facial verification with simple service"""
    try:
        facial_verification = FacialVerification.objects.get(id=facial_verification_id)
        
        facial_service = SimpleFacialService()
        
        # Basic image validation first
        is_valid, validation_msg = facial_service.validate_facial_image(
            facial_verification.facial_image.path
        )
        
        if not is_valid:
            facial_verification.status = 'failed'
            facial_verification.failure_reason = validation_msg
            facial_verification.save()
            return
        
        # Liveness detection
        is_live, liveness_score, liveness_details = facial_service.verify_liveness(
            facial_verification.facial_image.path
        )
        
        facial_verification.liveness_score = liveness_score
        facial_verification.liveness_passed = is_live
        
        # Face matching (if liveness passed)
        if is_live:
            # Get ID document image path for comparison
            id_image_path = facial_verification.id_verification.id_image_front.path
            
            is_match, match_score, match_details = facial_service.compare_faces_basic(
                id_image_path,
                facial_verification.facial_image.path
            )
            
            facial_verification.match_score = match_score
            facial_verification.match_passed = is_match
            
            if is_match:
                facial_verification.status = 'success'
                # Update user verification tier
                facial_verification.user.upgrade_verification_tier(3)
            else:
                facial_verification.status = 'failed'
                facial_verification.failure_reason = "Face matching failed"
        else:
            facial_verification.status = 'failed'
            facial_verification.failure_reason = "Liveness check failed"
        
        facial_verification.processed_at = timezone.now()
        facial_verification.save()
        
        logger.info(f"Facial verification processed: {facial_verification_id}")
        
    except Exception as e:
        logger.error(f"Facial verification task failed: {str(e)}")
        process_facial_verification.delay(facial_verification_id)

class VerificationStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, verification_id):
        try:
            verification = IDVerification.objects.get(
                id=verification_id,
                user=request.user
            )
            
            # Get facial verification if exists
            facial_verification = None
            try:
                facial_verification = FacialVerification.objects.get(
                    id_verification=verification
                )
            except FacialVerification.DoesNotExist:
                pass
            
            response_data = {
                'id_verification': IDVerificationSerializer(verification).data,
                'facial_verification': FacialVerificationSerializer(facial_verification).data if facial_verification else None,
                'overall_status': self._calculate_overall_status(verification, facial_verification)
            }
            
            return Response({
                'status': 'success',
                'data': response_data
            }, status=status.HTTP_200_OK)
            
        except IDVerification.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Verification not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _calculate_overall_status(self, id_verification, facial_verification):
        """Calculate overall verification status"""
        if not id_verification or id_verification.status != 'verified':
            return 'id_pending'
        
        if not facial_verification:
            return 'facial_pending'
        
        if facial_verification.status == 'success':
            return 'completed'
        elif facial_verification.status == 'failed':
            return 'facial_failed'
        else:
            return 'facial_processing'

class UserVerificationsView(generics.ListAPIView):
    serializer_class = IDVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return IDVerification.objects.filter(user=self.request.user).order_by('-created_at')

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_verification_status(request):
    """Get status for multiple verifications"""
    verification_ids = request.data.get('verification_ids', [])
    
    if not verification_ids:
        return Response({
            'status': 'error',
            'message': 'No verification IDs provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    verifications = IDVerification.objects.filter(
        id__in=verification_ids,
        user=request.user
    )
    
    data = {
        'verifications': IDVerificationSerializer(verifications, many=True).data
    }
    
    return Response({
        'status': 'success',
        'data': data
    }, status=status.HTTP_200_OK)

class VerificationWebhookView(APIView):
    """Webhook for external verification services"""
    permission_classes = [permissions.AllowAny]  # Note: Add proper authentication in production
    
    def post(self, request, verification_type):
        try:
            verification_id = request.data.get('verification_id')
            status = request.data.get('status')
            result_data = request.data.get('data', {})
            
            if verification_type == 'id':
                self._handle_id_verification_webhook(verification_id, status, result_data)
            elif verification_type == 'facial':
                self._handle_facial_verification_webhook(verification_id, status, result_data)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid verification type'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Webhook processing failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _handle_id_verification_webhook(self, verification_id, status, result_data):
        """Handle ID verification webhook"""
        try:
            verification = IDVerification.objects.get(id=verification_id)
            verification.government_response = result_data
            
            if status == 'verified':
                verification.mark_completed(
                    verified=True,
                    score=result_data.get('confidence_score', 0.9),
                    government_response=result_data
                )
            else:
                verification.mark_completed(
                    verified=False,
                    score=0.0,
                    government_response=result_data
                )
                
        except IDVerification.DoesNotExist:
            logger.error(f"ID verification not found: {verification_id}")
    
    def _handle_facial_verification_webhook(self, verification_id, status, result_data):
        """Handle facial verification webhook"""
        try:
            facial_verification = FacialVerification.objects.get(id=verification_id)
            facial_verification.status = status
            facial_verification.liveness_score = result_data.get('liveness_score', 0.0)
            facial_verification.match_score = result_data.get('match_score', 0.0)
            facial_verification.liveness_passed = result_data.get('liveness_passed', False)
            facial_verification.match_passed = result_data.get('match_passed', False)
            facial_verification.processed_at = timezone.now()
            facial_verification.save()
            
            # Update user verification tier if successful
            if status == 'success':
                facial_verification.user.upgrade_verification_tier(3)
                
        except FacialVerification.DoesNotExist:
            logger.error(f"Facial verification not found: {verification_id}")