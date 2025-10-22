import hashlib
import json
import statistics
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class BehavioralAnalyzer:
    """
    Analyzes behavioral biometrics to create profiles and verify users
    """
    
    def __init__(self):
        self.min_samples_for_profile = 10
        self.typing_confidence_threshold = 0.7
        self.touch_confidence_threshold = 0.6
    
    def create_biometric_signature(self, biometric_data: Dict[str, Any]) -> str:
        """
        Create a unique hash signature from biometric data
        """
        try:
            # Extract key features for signature
            signature_data = {
                'typing_rhythm': self._extract_typing_features(biometric_data.get('typing_pattern', {})),
                'touch_patterns': self._extract_touch_features(biometric_data.get('touch_patterns', {})),
                'device_id': biometric_data.get('device_characteristics', {}).get('device_id', '')
            }
            
            # Create deterministic JSON string (sorted keys)
            signature_string = json.dumps(signature_data, sort_keys=True)
            
            # Hash the signature
            signature_hash = hashlib.sha256(signature_string.encode()).hexdigest()
            
            return signature_hash
            
        except Exception as e:
            logger.error(f"Failed to create biometric signature: {str(e)}")
            return ""
    
    def verify_behavioral_match(self, current_data: Dict[str, Any], stored_profile: Dict[str, Any]) -> Tuple[bool, float, float]:
        """
        Verify if current behavioral data matches stored profile
        Returns: (is_match, confidence_score, risk_score)
        """
        try:
            confidence_factors = []
            risk_factors = []
            
            # Typing pattern verification
            if current_data.get('typing_pattern') and stored_profile.get('typical_hold_times'):
                typing_confidence = self._verify_typing_pattern(
                    current_data['typing_pattern'],
                    stored_profile
                )
                confidence_factors.append(typing_confidence * 0.5)  # 50% weight
            
            # Touch pattern verification
            if current_data.get('touch_patterns') and stored_profile.get('avg_swipe_speed'):
                touch_confidence = self._verify_touch_patterns(
                    current_data['touch_patterns'],
                    stored_profile
                )
                confidence_factors.append(touch_confidence * 0.3)  # 30% weight
            
            # Device verification
            if current_data.get('device_characteristics'):
                device_confidence = self._verify_device(
                    current_data['device_characteristics'],
                    stored_profile
                )
                confidence_factors.append(device_confidence * 0.2)  # 20% weight
            
            # Calculate overall confidence
            if confidence_factors:
                overall_confidence = sum(confidence_factors)
            else:
                overall_confidence = 0.0
            
            # Calculate risk score (inverse of confidence with some adjustments)
            risk_score = max(0.0, 1.0 - overall_confidence)
            
            # Adjust for anomaly detection
            anomalies = self._detect_anomalies(current_data, stored_profile)
            if anomalies:
                risk_score = min(1.0, risk_score + (len(anomalies) * 0.2))
            
            is_match = overall_confidence >= 0.7  # Adjust threshold as needed
            
            return is_match, overall_confidence, risk_score
            
        except Exception as e:
            logger.error(f"Behavioral verification failed: {str(e)}")
            return False, 0.0, 1.0
    
    def _extract_typing_features(self, typing_pattern: Dict[str, Any]) -> Dict[str, float]:
        """Extract key features from typing pattern"""
        features = {}
        
        try:
            hold_times = typing_pattern.get('key_hold_times', [])
            flight_times = typing_pattern.get('flight_times', [])
            
            if hold_times:
                # Calculate statistics for hold times
                if isinstance(hold_times[0], dict):
                    # Format: [{'key': 'a', 'hold_time': 150}, ...]
                    hold_values = [item.get('hold_time', 0) for item in hold_times if item.get('hold_time')]
                else:
                    # Format: [150, 200, ...]
                    hold_values = hold_times
                
                if hold_values:
                    features['avg_hold_time'] = statistics.mean(hold_values)
                    features['hold_time_std'] = statistics.stdev(hold_values) if len(hold_values) > 1 else 0
            
            if flight_times:
                features['avg_flight_time'] = statistics.mean(flight_times)
                features['flight_time_std'] = statistics.stdev(flight_times) if len(flight_times) > 1 else 0
            
        except Exception as e:
            logger.warning(f"Failed to extract typing features: {str(e)}")
        
        return features
    
    def _extract_touch_features(self, touch_patterns: Dict[str, Any]) -> Dict[str, float]:
        """Extract key features from touch patterns"""
        features = {}
        
        try:
            swipe_data = touch_patterns.get('swipe_speeds', [])
            touch_data = touch_patterns.get('touch_pressures', [])
            
            if swipe_data:
                features['avg_swipe_speed'] = statistics.mean(swipe_data)
                features['swipe_speed_std'] = statistics.stdev(swipe_data) if len(swipe_data) > 1 else 0
            
            if touch_data:
                features['avg_touch_pressure'] = statistics.mean(touch_data)
                features['touch_pressure_std'] = statistics.stdev(touch_data) if len(touch_data) > 1 else 0
            
        except Exception as e:
            logger.warning(f"Failed to extract touch features: {str(e)}")
        
        return features
    
    def _verify_typing_pattern(self, current_typing: Dict[str, Any], stored_profile: Dict[str, Any]) -> float:
        """Verify typing pattern against stored profile"""
        try:
            current_features = self._extract_typing_features(current_typing)
            similarity_score = 0.0
            
            # Compare average hold times
            if 'avg_hold_time' in current_features and stored_profile.get('typical_hold_times'):
                stored_avg = stored_profile.get('avg_typing_speed', 0)  # This might need adjustment
                current_avg = current_features['avg_hold_time']
                
                # Calculate similarity (within 20% difference)
                difference = abs(stored_avg - current_avg) / max(stored_avg, 1)
                if difference <= 0.2:
                    similarity_score += 0.7
                elif difference <= 0.4:
                    similarity_score += 0.3
            
            return min(similarity_score, 1.0)
            
        except Exception as e:
            logger.error(f"Typing pattern verification failed: {str(e)}")
            return 0.0
    
    def _verify_touch_patterns(self, current_touch: Dict[str, Any], stored_profile: Dict[str, Any]) -> float:
        """Verify touch patterns against stored profile"""
        try:
            current_features = self._extract_touch_features(current_touch)
            similarity_score = 0.0
            
            # Compare swipe speeds
            if 'avg_swipe_speed' in current_features and stored_profile.get('avg_swipe_speed'):
                stored_speed = stored_profile['avg_swipe_speed']
                current_speed = current_features['avg_swipe_speed']
                
                difference = abs(stored_speed - current_speed) / max(stored_speed, 1)
                if difference <= 0.3:
                    similarity_score += 0.5
            
            # Compare touch pressures
            if 'avg_touch_pressure' in current_features and stored_profile.get('typical_touch_pressure'):
                stored_pressure = stored_profile['typical_touch_pressure']
                current_pressure = current_features['avg_touch_pressure']
                
                difference = abs(stored_pressure - current_pressure) / max(stored_pressure, 1)
                if difference <= 0.25:
                    similarity_score += 0.5
            
            return min(similarity_score, 1.0)
            
        except Exception as e:
            logger.error(f"Touch pattern verification failed: {str(e)}")
            return 0.0
    
    def _verify_device(self, current_device: Dict[str, Any], stored_profile: Dict[str, Any]) -> float:
        """Verify device characteristics"""
        try:
            current_device_id = current_device.get('device_id')
            trusted_devices = stored_profile.get('trusted_devices', [])
            
            if current_device_id and current_device_id in trusted_devices:
                return 1.0  # Exact device match
            
            # Partial device matching (OS, screen size, etc.)
            device_similarity = 0.0
            
            current_os = current_device.get('os')
            stored_typical_os = stored_profile.get('device_characteristics', {}).get('typical_os')
            
            if current_os and stored_typical_os and current_os == stored_typical_os:
                device_similarity += 0.5
            
            return device_similarity
            
        except Exception as e:
            logger.error(f"Device verification failed: {str(e)}")
            return 0.0
    
    def _detect_anomalies(self, current_data: Dict[str, Any], stored_profile: Dict[str, Any]) -> List[str]:
        """Detect behavioral anomalies"""
        anomalies = []
        
        try:
            # Check for extreme typing speed variations
            current_typing = self._extract_typing_features(current_data.get('typing_pattern', {}))
            if 'avg_hold_time' in current_typing and stored_profile.get('avg_typing_speed'):
                stored_speed = stored_profile['avg_typing_speed']
                current_speed = current_typing['avg_hold_time']
                
                difference = abs(stored_speed - current_speed) / max(stored_speed, 1)
                if difference > 0.5:  # 50% difference
                    anomalies.append('typing_speed_anomaly')
            
            # Check for unfamiliar device
            current_device = current_data.get('device_characteristics', {})
            trusted_devices = stored_profile.get('trusted_devices', [])
            
            current_device_id = current_device.get('device_id')
            if current_device_id and current_device_id not in trusted_devices:
                anomalies.append('unfamiliar_device')
            
        except Exception as e:
            logger.warning(f"Anomaly detection failed: {str(e)}")
        
        return anomalies
    
    def update_biometric_profile(self, profile_data: Dict[str, Any], new_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update biometric profile with new samples (incremental learning)
        """
        try:
            if not new_samples:
                return profile_data
            
            # Update typing patterns
            typing_samples = [s.get('typing_pattern', {}) for s in new_samples if s.get('typing_pattern')]
            if typing_samples:
                profile_data = self._update_typing_profile(profile_data, typing_samples)
            
            # Update touch patterns
            touch_samples = [s.get('touch_patterns', {}) for s in new_samples if s.get('touch_patterns')]
            if touch_samples:
                profile_data = self._update_touch_profile(profile_data, touch_samples)
            
            # Update device patterns
            device_samples = [s.get('device_characteristics', {}) for s in new_samples if s.get('device_characteristics')]
            if device_samples:
                profile_data = self._update_device_profile(profile_data, device_samples)
            
            # Update sample count
            profile_data['samples_collected'] += len(new_samples)
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Profile update failed: {str(e)}")
            return profile_data
    
    def _update_typing_profile(self, profile: Dict[str, Any], new_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update typing profile with new samples"""
        # Implementation for incremental learning of typing patterns
        # This is a simplified version - expand based on your needs
        return profile
    
    def _update_touch_profile(self, profile: Dict[str, Any], new_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update touch profile with new samples"""
        # Implementation for incremental learning of touch patterns
        return profile
    
    def _update_device_profile(self, profile: Dict[str, Any], new_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update device profile with new samples"""
        # Add new trusted devices
        trusted_devices = set(profile.get('trusted_devices', []))
        
        for sample in new_samples:
            device_id = sample.get('device_id')
            if device_id and device_id not in trusted_devices:
                trusted_devices.add(device_id)
        
        profile['trusted_devices'] = list(trusted_devices)
        return profile