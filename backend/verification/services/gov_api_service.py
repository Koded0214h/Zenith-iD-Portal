import requests
import json
import time
import logging
import os
import base64
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class GovernmentAPIService:
    def __init__(self):
        # VerifyMe Configuration
        self.verifyme_base_url = os.getenv('VERIFYME_BASE_URL', '')
        self.verifyme_api_key = os.getenv('VERIFYME_API_KEY', '')
        self.verifyme_secret_key = os.getenv('VERIFYME_SECRET_KEY', '')
        self.use_mock = os.getenv('USE_MOCK_VERIFICATION', 'True').lower() == 'true'
        self.api_timeout = 30
        self.max_retries = 3
        
        logger.info(f"GovernmentAPIService initialized - Mock Mode: {self.use_mock}")
        logger.info(f"VerifyMe Configured: {bool(self.verifyme_base_url and self.verifyme_api_key)}")

    def verify_nin(self, nin_number: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify NIN using VerifyMe API
        """
        if not (self.verifyme_base_url and self.verifyme_api_key) or self.use_mock:
            return self._mock_nin_verification(nin_number, user_data)
        
        return self._verifyme_nin_verification(nin_number, user_data)

    def verify_bvn(self, bvn_number: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify BVN using VerifyMe API
        """
        if not (self.verifyme_base_url and self.verifyme_api_key) or self.use_mock:
            return self._mock_bvn_verification(bvn_number, user_data)
        
        return self._verifyme_bvn_verification(bvn_number, user_data)

    def _verifyme_nin_verification(self, nin_number: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify NIN with VerifyMe API
        """
        payload = {
            "number": nin_number,
            "firstname": user_data.get('first_name', ''),
            "lastname": user_data.get('last_name', ''),
            "dob": user_data.get('date_of_birth', ''),
            "type": "nin"
        }
        
        return self._make_verifyme_request(payload, "NIN")

    def _verifyme_bvn_verification(self, bvn_number: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify BVN with VerifyMe API
        """
        payload = {
            "number": bvn_number,
            "firstname": user_data.get('first_name', ''),
            "lastname": user_data.get('last_name', ''),
            "dob": user_data.get('date_of_birth', ''),
            "type": "bvn"
        }
        
        return self._make_verifyme_request(payload, "BVN")

    def _make_verifyme_request(self, payload: Dict[str, Any], verification_type: str) -> Dict[str, Any]:
        """
        Make request to VerifyMe API
        """
        url = f"{self.verifyme_base_url}"
        headers = self._build_verifyme_headers()
        
        logger.info(f"Making {verification_type} verification request to VerifyMe")
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.api_timeout
                )
                
                response_time = time.time() - start_time
                response_data = response.json()
                
                logger.info(f"VerifyMe {verification_type} Response: {response.status_code}")
                
                if response.status_code == 200:
                    return self._parse_verifyme_response(response_data, response_time, verification_type)
                else:
                    logger.warning(
                        f"VerifyMe {verification_type} verification failed. "
                        f"Status: {response.status_code}, Attempt: {attempt + 1}"
                    )
                    
                    if attempt == self.max_retries - 1:
                        return {
                            'verified': False,
                            'response_time': response_time,
                            'error': f"HTTP {response.status_code}: {response_data.get('message', 'Unknown error')}",
                            'status': 'failed'
                        }
                
            except requests.exceptions.Timeout:
                logger.error(f"VerifyMe {verification_type} verification timeout. Attempt: {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return {
                        'verified': False,
                        'response_time': self.api_timeout,
                        'error': 'VerifyMe API timeout',
                        'status': 'timeout'
                    }
            
            except requests.exceptions.RequestException as e:
                logger.error(f"VerifyMe {verification_type} request error: {str(e)}")
                if attempt == self.max_retries - 1:
                    return {
                        'verified': False,
                        'response_time': 0,
                        'error': f'VerifyMe request failed: {str(e)}',
                        'status': 'failed'
                    }
            
            # Exponential backoff
            time.sleep(2 ** attempt)
        
        return {
            'verified': False,
            'response_time': 0,
            'error': 'Max retries exceeded',
            'status': 'failed'
        }

    def _build_verifyme_headers(self) -> Dict[str, str]:
        """Build headers for VerifyMe API"""
        credentials = f"{self.verifyme_api_key}:{self.verifyme_secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {encoded_credentials}',
            'User-Agent': 'Zenith-iD-Portal/1.0'
        }

    def _parse_verifyme_response(self, response_data: Dict, response_time: float, verification_type: str) -> Dict[str, Any]:
        """Parse VerifyMe API response"""
        status = response_data.get('status', '').lower()
        verified = status == 'success'
        
        return {
            'verified': verified,
            'match_score': 1.0 if verified else 0.0,
            'response_data': response_data,
            'response_time': response_time,
            'status': 'success',
            'message': response_data.get('message', 'Verification completed')
        }

    # Keep the mock verification methods from previous version
    def _mock_nin_verification(self, nin_number: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock NIN verification for development"""
        logger.warning("Using MOCK NIN verification - configure VerifyMe API in production")
        time.sleep(1.5)
        
        is_valid = (
            len(nin_number) == 11 and
            nin_number.isdigit() and
            user_data.get('first_name') and
            user_data.get('last_name')
        )
        
        return {
            'verified': is_valid,
            'match_score': 0.95 if is_valid else 0.1,
            'response_data': {
                'mock': True,
                'status': 'success' if is_valid else 'failed',
                'message': 'Mock NIN verification - configure VerifyMe API',
                'type': 'nin',
                'number': nin_number
            },
            'response_time': 1.5,
            'status': 'success' if is_valid else 'failed'
        }

    def _mock_bvn_verification(self, bvn_number: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock BVN verification for development"""
        logger.warning("Using MOCK BVN verification - configure VerifyMe API in production")
        time.sleep(2.0)
        
        is_valid = (
            len(bvn_number) == 11 and
            bvn_number.isdigit() and
            user_data.get('first_name') and
            user_data.get('last_name')
        )
        
        return {
            'verified': is_valid,
            'match_score': 0.92 if is_valid else 0.1,
            'response_data': {
                'mock': True,
                'status': 'success' if is_valid else 'failed',
                'message': 'Mock BVN verification - configure VerifyMe API',
                'type': 'bvn',
                'number': bvn_number
            },
            'response_time': 2.0,
            'status': 'success' if is_valid else 'failed'
        }