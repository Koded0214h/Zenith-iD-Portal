import cv2
import pytesseract
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.ocr_engine = pytesseract
        self.supported_languages = ['eng']
    
    def process_id_document(self, image_path: str, id_type: str) -> Dict[str, Any]:
        """
        Process ID document using OCR and extract relevant information
        """
        try:
            # Read and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not read image file")
            
            processed_image = self._preprocess_image(image)
            
            # Extract text using Tesseract with optimized configuration
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/-:. '
            extracted_text = self.ocr_engine.image_to_string(processed_image, config=config)
            
            # Parse extracted data based on ID type
            parsed_data = self._parse_extracted_data(extracted_text, id_type)
            
            # Calculate confidence score
            confidence_data = self.ocr_engine.image_to_data(processed_image, output_type=self.ocr_engine.Output.DICT)
            confidence_score = self._calculate_confidence(confidence_data)
            
            parsed_data['raw_text'] = extracted_text
            parsed_data['ocr_confidence'] = confidence_score
            
            logger.info(f"OCR processing completed for {id_type}. Confidence: {confidence_score}")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"OCR processing failed for {id_type}: {str(e)}")
            raise Exception(f"OCR processing failed: {str(e)}")
    
    def _preprocess_image(self, image):
        """Preprocess image for better OCR results"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply noise reduction
        denoised = cv2.medianBlur(gray, 3)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Apply morphological operations to clean up image
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def _parse_extracted_data(self, text: str, id_type: str) -> Dict[str, Any]:
        """Parse extracted text based on ID type"""
        parsing_strategies = {
            'nin': self._parse_nin_data,
            'voters_card': self._parse_voters_card_data,
            'passport': self._parse_passport_data,
            'drivers_license': self._parse_drivers_license_data,
        }
        
        parser = parsing_strategies.get(id_type, self._parse_generic_data)
        return parser(text)
    
    def _parse_nin_data(self, text: str) -> Dict[str, Any]:
        """Parse NIN document data"""
        data = {}
        
        # Extract NIN (11-digit number)
        nin_match = re.search(r'\b\d{11}\b', text)
        if nin_match:
            data['id_number'] = nin_match.group()
        
        # Extract name (typically in all caps)
        name_match = re.search(r'([A-Z]{2,}(?:\s+[A-Z]{2,})+)', text)
        if name_match:
            data['full_name'] = name_match.group().title()
        
        # Extract date of birth
        dob_match = re.search(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b', text)
        if dob_match:
            data['date_of_birth'] = self._parse_date(dob_match.group())
        
        return data
    
    def _parse_voters_card_data(self, text: str) -> Dict[str, Any]:
        """Parse Voter's Card data"""
        data = {}
        
        # Extract VIN (19-character code)
        vin_match = re.search(r'[A-Z0-9]{19}', text)
        if vin_match:
            data['id_number'] = vin_match.group()
        
        # Extract name
        name_match = re.search(r'Name[:\s]*([A-Za-z\s]+)', text, re.IGNORECASE)
        if name_match:
            data['full_name'] = name_match.group(1).strip().title()
        
        return data
    
    def _parse_passport_data(self, text: str) -> Dict[str, Any]:
        """Parse Passport data"""
        data = {}
        
        # Extract passport number (typically 9 characters with letters and digits)
        passport_match = re.search(r'[A-Z][0-9]{8}', text)
        if passport_match:
            data['id_number'] = passport_match.group()
        
        # Extract name from P< line in machine-readable zone
        mrz_match = re.search(r'P<[A-Z]{3}[A-Z<]+<+', text)
        if mrz_match:
            # Parse machine-readable zone
            mrz_data = self._parse_mrz(mrz_match.group())
            data.update(mrz_data)
        
        return data
    
    def _parse_drivers_license_data(self, text: str) -> Dict[str, Any]:
        """Parse Driver's License data"""
        data = {}
        
        # Extract license number (varies by country)
        license_match = re.search(r'[A-Z0-9]{5,15}', text)
        if license_match:
            data['id_number'] = license_match.group()
        
        return data
    
    def _parse_generic_data(self, text: str) -> Dict[str, Any]:
        """Generic parser for unknown ID types"""
        data = {}
        
        # Try to extract any potential ID numbers
        id_matches = re.findall(r'[A-Z0-9]{5,20}', text)
        if id_matches:
            data['potential_id_numbers'] = id_matches
        
        return data
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse various date formats to ISO format"""
        try:
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%Y/%m/%d']:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        except:
            pass
        return None
    
    def _parse_mrz(self, mrz_line: str) -> Dict[str, Any]:
        """Parse Machine Readable Zone from passports"""
        data = {}
        try:
            # Basic MRZ parsing - extend based on specific format
            parts = mrz_line.split('<')
            if len(parts) > 1:
                data['surname'] = parts[0].replace('P<', '').title()
                data['given_names'] = parts[1].title() if len(parts) > 1 else ''
        except:
            pass
        return data
    
    def _calculate_confidence(self, confidence_data: Dict) -> float:
        """Calculate overall OCR confidence score"""
        confidences = [float(conf) for conf in confidence_data['conf'] if int(conf) != -1]
        if not confidences:
            return 0.0
        
        return sum(confidences) / len(confidences) / 100.0  # Normalize to 0-1