import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

class LightweightFacialService:
    """
    Lightweight facial recognition without TensorFlow
    Uses OpenCV and basic image processing
    """
    
    def __init__(self):
        try:
            # Load OpenCV face detection models
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
            logger.info("Lightweight facial service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize facial service: {str(e)}")
            raise

    def verify_liveness(self, image_path: str) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Basic liveness detection using image analysis
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return False, 0.0, {'error': 'Could not read image'}
            
            # Basic image quality checks
            quality_score = self._check_image_quality(image)
            
            # Face detection
            faces = self.face_cascade.detectMultiScale(
                cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(100, 100)
            )
            
            if len(faces) == 0:
                return False, 0.0, {'error': 'No face detected'}
            
            # Multiple verification methods
            verification_score = 0.0
            verification_details = {'checks_passed': []}
            
            # Check 1: Face detection
            verification_score += 0.3
            verification_details['checks_passed'].append('face_detected')
            
            # Check 2: Eye detection
            eye_count = self._detect_eyes(image, faces[0])
            if eye_count >= 2:
                verification_score += 0.3
                verification_details['checks_passed'].append('eyes_detected')
            
            # Check 3: Image quality
            if quality_score > 0.7:
                verification_score += 0.2
                verification_details['checks_passed'].append('good_quality')
            
            # Check 4: Color analysis (basic spoof detection)
            color_score = self._analyze_colors(image, faces[0])
            verification_score += color_score * 0.2
            if color_score > 0.5:
                verification_details['checks_passed'].append('natural_colors')
            
            is_live = verification_score >= 0.7
            verification_details['final_score'] = verification_score
            
            logger.info(f"Liveness check completed. Score: {verification_score}")
            
            return is_live, verification_score, verification_details
            
        except Exception as e:
            logger.error(f"Liveness verification failed: {str(e)}")
            return False, 0.0, {'error': str(e)}

    def _check_image_quality(self, image: np.ndarray) -> float:
        """Check basic image quality metrics"""
        try:
            # Check image dimensions
            height, width = image.shape[:2]
            if height < 300 or width < 300:
                return 0.3
            
            # Check image sharpness (using Laplacian variance)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Check brightness
            brightness = np.mean(gray)
            
            # Normalize scores
            sharpness_score = min(sharpness / 100.0, 1.0)  # Assuming 100 is good sharpness
            brightness_score = 1.0 - abs(brightness - 127) / 127  # Ideal around 127
            
            return (sharpness_score + brightness_score) / 2.0
            
        except Exception as e:
            logger.error(f"Image quality check failed: {str(e)}")
            return 0.0

    def _detect_eyes(self, image: np.ndarray, face_bbox: Tuple) -> int:
        """Detect eyes within face region"""
        try:
            x, y, w, h = face_bbox
            face_roi = image[y:y+h, x:x+w]
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            
            eyes = self.eye_cascade.detectMultiScale(
                gray_face,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            return len(eyes)
        except Exception as e:
            logger.error(f"Eye detection failed: {str(e)}")
            return 0

    def _analyze_colors(self, image: np.ndarray, face_bbox: Tuple) -> float:
        """Basic color analysis for spoof detection"""
        try:
            x, y, w, h = face_bbox
            face_roi = image[y:y+h, x:x+w]
            
            # Convert to different color spaces
            hsv = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
            lab = cv2.cvtColor(face_roi, cv2.COLOR_BGR2LAB)
            
            # Calculate color variances (real faces have more color variation)
            hsv_var = np.var(hsv, axis=(0, 1))
            lab_var = np.var(lab, axis=(0, 1))
            
            # Combine variances
            total_variance = np.mean(hsv_var) + np.mean(lab_var)
            
            # Normalize to 0-1 score (empirical threshold)
            return min(total_variance / 5000.0, 1.0)
            
        except Exception as e:
            logger.error(f"Color analysis failed: {str(e)}")
            return 0.0

    def compare_faces_basic(self, image1_path: str, image2_path: str) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Basic face comparison using feature matching
        """
        try:
            img1 = cv2.imread(image1_path)
            img2 = cv2.imread(image2_path)
            
            if img1 is None or img2 is None:
                return False, 0.0, {'error': 'Could not read one or both images'}
            
            # Use ORB feature matching
            orb = cv2.ORB_create()
            kp1, des1 = orb.detectAndCompute(img1, None)
            kp2, des2 = orb.detectAndCompute(img2, None)
            
            if des1 is None or des2 is None:
                return False, 0.0, {'error': 'No features detected in one or both images'}
            
            # Feature matching
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            
            if len(matches) == 0:
                return False, 0.0, {'error': 'No feature matches found'}
            
            # Calculate match score
            distances = [m.distance for m in matches]
            avg_distance = np.mean(distances)
            
            # Convert to similarity score (lower distance = higher similarity)
            similarity = max(0.0, 1.0 - (avg_distance / 100.0))
            
            is_match = similarity >= 0.6  # Adjust threshold as needed
            
            details = {
                'matches_count': len(matches),
                'avg_distance': avg_distance,
                'similarity_score': similarity,
                'method': 'ORB_feature_matching'
            }
            
            logger.info(f"Face comparison completed. Similarity: {similarity}")
            
            return is_match, similarity, details
            
        except Exception as e:
            logger.error(f"Face comparison failed: {str(e)}")
            return False, 0.0, {'error': str(e)}