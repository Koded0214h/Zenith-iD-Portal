from celery import shared_task
from django.utils import timezone
import logging

from .models import IDVerification, FacialVerification
from .services.ocr_service import OCRService
from .services.facial_service import FacialRecognitionService
from .services.gov_api_service import GovernmentAPIService

logger = logging.getLogger(__name__)

@shared_task
def process_id_verification(verification_id):
    """Process ID verification asynchronously"""
    try:
        verification = IDVerification.objects.get(id=verification_id)
        verification.mark_processing()
        
        # Step 1: OCR Processing
        ocr_service = OCRService()
        ocr_result = ocr_service.process_id_document(
            verification.id_image_front.path,
            verification.id_type
        )
        
        verification.extracted_data = ocr_result
        verification.ocr_confidence = ocr_result.get('ocr_confidence', 0.0)
        verification.id_number = ocr_result.get('id_number', '')
        verification.save()
        
        # Step 2: Government API Verification
        if verification.id_number:
            gov_service = GovernmentAPIService()
            
            if verification.id_type == 'nin':
                gov_result = gov_service.verify_nin(
                    verification.id_number,
                    {
                        'first_name': verification.user.first_name,
                        'last_name': verification.user.last_name,
                        'date_of_birth': ocr_result.get('date_of_birth')
                    }
                )
            elif verification.id_type == 'bvn':
                gov_result = gov_service.verify_bvn(
                    verification.id_number,
                    {
                        'first_name': verification.user.first_name,
                        'last_name': verification.user.last_name,
                        'phone_number': verification.user.phone_number
                    }
                )
            else:
                # For other ID types, use generic verification
                gov_result = {'verified': True, 'match_score': 0.8}  # Mock
            
            # Update verification with government results
            verification.government_verified = gov_result.get('verified', False)
            verification.verification_score = gov_result.get('match_score', 0.0)
            verification.government_response = gov_result
            
            if gov_result.get('verified', False):
                verification.mark_completed(
                    verified=True,
                    score=gov_result.get('match_score', 0.0),
                    government_response=gov_result
                )
            else:
                verification.mark_completed(
                    verified=False,
                    score=0.0,
                    government_response=gov_result
                )
        
        logger.info(f"ID verification processed: {verification_id}")
        
    except Exception as e:
        logger.error(f"ID verification task failed for {verification_id}: {str(e)}")
        try:
            verification = IDVerification.objects.get(id=verification_id)
            verification.status = 'failed'
            verification.failure_reason = str(e)
            verification.save()
        except:
            pass

@shared_task
def process_facial_verification(facial_verification_id):
    """Process facial verification asynchronously"""
    try:
        facial_verification = FacialVerification.objects.get(id=facial_verification_id)
        
        facial_service = FacialRecognitionService()
        
        # Step 1: Liveness Detection
        is_live, liveness_score, liveness_details = facial_service.verify_liveness(
            facial_verification.facial_image.path
        )
        
        facial_verification.liveness_score = liveness_score
        facial_verification.liveness_passed = is_live
        
        # Step 2: Face Matching (if liveness passed)
        if is_live:
            # Extract ID photo from ID verification (you might need to store this separately)
            id_photo_data = ""  # You'll need to extract this from the ID document
            
            is_match, match_score, match_details = facial_service.compare_faces(
                id_photo_data,
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
        else:
            facial_verification.status = 'failed'
        
        facial_verification.processed_at = timezone.now()
        facial_verification.save()
        
        logger.info(f"Facial verification processed: {facial_verification_id}")
        
    except Exception as e:
        logger.error(f"Facial verification task failed for {facial_verification_id}: {str(e)}")
        try:
            facial_verification = FacialVerification.objects.get(id=facial_verification_id)
            facial_verification.status = 'failed'
            facial_verification.save()
        except:
            pass