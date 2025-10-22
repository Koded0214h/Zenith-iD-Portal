import hashlib
import json
import statistics
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class WebBehaviorAnalyzer:
    """
    Analyzes web-specific behavioral biometrics
    """
    
    def __init__(self):
        self.min_mouse_samples = 5
        self.min_keystroke_samples = 3
    
    def create_web_behavioral_signature(self, web_data: Dict[str, Any]) -> str:
        """
        Create unique signature from web behavioral data
        """
        try:
            signature_data = {
                'mouse_patterns': self._extract_mouse_features(web_data.get('mouse_movements', [])),
                'scroll_patterns': self._extract_scroll_features(web_data.get('scroll_events', [])),
                'typing_rhythm': self._extract_web_typing_features(web_data.get('keystroke_timing', [])),
                'browser_fingerprint': self._create_browser_fingerprint(web_data.get('browser_info', {}))
            }
            
            signature_string = json.dumps(signature_data, sort_keys=True)
            return hashlib.sha256(signature_string.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to create web behavioral signature: {str(e)}")
            return ""
    
    def verify_web_behavior(self, current_data: Dict[str, Any], stored_profile: Dict[str, Any]) -> Tuple[bool, float, float]:
        """
        Verify web behavioral data against stored profile
        """
        try:
            confidence_factors = []
            risk_factors = []
            
            # Mouse movement verification
            if current_data.get('mouse_movements') and stored_profile.get('mouse_patterns'):
                mouse_confidence = self._verify_mouse_patterns(
                    current_data['mouse_movements'],
                    stored_profile['mouse_patterns']
                )
                confidence_factors.append(mouse_confidence * 0.4)
            
            # Keystroke timing verification
            if current_data.get('keystroke_timing') and stored_profile.get('typing_rhythm'):
                typing_confidence = self._verify_web_typing(
                    current_data['keystroke_timing'],
                    stored_profile['typing_rhythm']
                )
                confidence_factors.append(typing_confidence * 0.3)
            
            # Scroll behavior verification
            if current_data.get('scroll_events') and stored_profile.get('scroll_patterns'):
                scroll_confidence = self._verify_scroll_behavior(
                    current_data['scroll_events'],
                    stored_profile['scroll_patterns']
                )
                confidence_factors.append(scroll_confidence * 0.2)
            
            # Browser fingerprint verification
            if current_data.get('browser_info'):
                browser_confidence = self._verify_browser_fingerprint(
                    current_data['browser_info'],
                    stored_profile.get('browser_fingerprint', {})
                )
                confidence_factors.append(browser_confidence * 0.1)
            
            # Calculate overall confidence
            overall_confidence = sum(confidence_factors) if confidence_factors else 0.0
            risk_score = max(0.0, 1.0 - overall_confidence)
            
            # Detect web-specific anomalies
            anomalies = self._detect_web_anomalies(current_data, stored_profile)
            if anomalies:
                risk_score = min(1.0, risk_score + (len(anomalies) * 0.15))
            
            is_match = overall_confidence >= 0.65  # Slightly lower threshold for web
            
            return is_match, overall_confidence, risk_score
            
        except Exception as e:
            logger.error(f"Web behavior verification failed: {str(e)}")
            return False, 0.0, 1.0
    
    def _extract_mouse_features(self, mouse_movements: List[Dict]) -> Dict[str, float]:
        """Extract features from mouse movement data"""
        features = {}
        
        try:
            if not mouse_movements:
                return features
            
            # Extract movement speeds
            speeds = [movement.get('speed', 0) for movement in mouse_movements if movement.get('speed')]
            if speeds:
                features['avg_mouse_speed'] = statistics.mean(speeds)
                features['mouse_speed_std'] = statistics.stdev(speeds) if len(speeds) > 1 else 0
            
            # Extract movement patterns (simplified)
            movement_angles = []
            for i in range(1, len(mouse_movements)):
                if all(key in mouse_movements[i] for key in ['x', 'y']) and all(key in mouse_movements[i-1] for key in ['x', 'y']):
                    dx = mouse_movements[i]['x'] - mouse_movements[i-1]['x']
                    dy = mouse_movements[i]['y'] - mouse_movements[i-1]['y']
                    if dx != 0:
                        angle = abs(dy / dx)
                        movement_angles.append(angle)
            
            if movement_angles:
                features['avg_movement_angle'] = statistics.mean(movement_angles)
            
        except Exception as e:
            logger.warning(f"Mouse feature extraction failed: {str(e)}")
        
        return features
    
    def _extract_scroll_features(self, scroll_events: List[Dict]) -> Dict[str, float]:
        """Extract features from scroll behavior"""
        features = {}
        
        try:
            if not scroll_events:
                return features
            
            speeds = [event.get('speed', 0) for event in scroll_events if event.get('speed')]
            if speeds:
                features['avg_scroll_speed'] = statistics.mean(speeds)
                features['scroll_speed_std'] = statistics.stdev(speeds) if len(speeds) > 1 else 0
            
            # Direction patterns
            directions = [event.get('direction', '') for event in scroll_events if event.get('direction')]
            if directions:
                features['preferred_direction'] = max(set(directions), key=directions.count)
            
        except Exception as e:
            logger.warning(f"Scroll feature extraction failed: {str(e)}")
        
        return features
    
    def _extract_web_typing_features(self, keystroke_timing: List[Dict]) -> Dict[str, float]:
        """Extract typing features from web keystroke data"""
        features = {}
        
        try:
            if not keystroke_timing:
                return features
            
            hold_times = [ks.get('hold_time', 0) for ks in keystroke_timing if ks.get('hold_time')]
            flight_times = [ks.get('next_key_delay', 0) for ks in keystroke_timing if ks.get('next_key_delay')]
            
            if hold_times:
                features['avg_hold_time'] = statistics.mean(hold_times)
                features['hold_time_std'] = statistics.stdev(hold_times) if len(hold_times) > 1 else 0
            
            if flight_times:
                features['avg_flight_time'] = statistics.mean(flight_times)
                features['flight_time_std'] = statistics.stdev(flight_times) if len(flight_times) > 1 else 0
            
        except Exception as e:
            logger.warning(f"Web typing feature extraction failed: {str(e)}")
        
        return features
    
    def _create_browser_fingerprint(self, browser_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create browser fingerprint from available data"""
        fingerprint = {}
        
        try:
            if browser_info:
                fingerprint = {
                    'user_agent': browser_info.get('userAgent', ''),
                    'language': browser_info.get('language', ''),
                    'platform': browser_info.get('platform', ''),
                    'hardware_concurrency': browser_info.get('hardwareConcurrency', ''),
                    'device_memory': browser_info.get('deviceMemory', ''),
                    'screen_resolution': browser_info.get('screen', {}),
                    'timezone': browser_info.get('timezone', ''),
                    'canvas_fingerprint': browser_info.get('canvas', ''),
                    'webgl_fingerprint': browser_info.get('webgl', '')
                }
        except Exception as e:
            logger.warning(f"Browser fingerprint creation failed: {str(e)}")
        
        return fingerprint
    
    def _verify_mouse_patterns(self, current_movements: List[Dict], stored_patterns: Dict[str, float]) -> float:
        """Verify mouse movement patterns"""
        try:
            current_features = self._extract_mouse_features(current_movements)
            similarity = 0.0
            
            if 'avg_mouse_speed' in current_features and 'avg_mouse_speed' in stored_patterns:
                current_speed = current_features['avg_mouse_speed']
                stored_speed = stored_patterns['avg_mouse_speed']
                
                difference = abs(stored_speed - current_speed) / max(stored_speed, 1)
                if difference <= 0.3:
                    similarity += 0.7
            
            return min(similarity, 1.0)
            
        except Exception as e:
            logger.error(f"Mouse pattern verification failed: {str(e)}")
            return 0.0
    
    def _verify_web_typing(self, current_typing: List[Dict], stored_rhythm: Dict[str, float]) -> float:
        """Verify web typing patterns"""
        try:
            current_features = self._extract_web_typing_features(current_typing)
            similarity = 0.0
            
            if 'avg_hold_time' in current_features and 'avg_hold_time' in stored_rhythm:
                current_hold = current_features['avg_hold_time']
                stored_hold = stored_rhythm['avg_hold_time']
                
                difference = abs(stored_hold - current_hold) / max(stored_hold, 1)
                if difference <= 0.25:
                    similarity += 0.5
            
            if 'avg_flight_time' in current_features and 'avg_flight_time' in stored_rhythm:
                current_flight = current_features['avg_flight_time']
                stored_flight = stored_rhythm['avg_flight_time']
                
                difference = abs(stored_flight - current_flight) / max(stored_flight, 1)
                if difference <= 0.3:
                    similarity += 0.5
            
            return min(similarity, 1.0)
            
        except Exception as e:
            logger.error(f"Web typing verification failed: {str(e)}")
            return 0.0
    
    def _verify_scroll_behavior(self, current_scroll: List[Dict], stored_patterns: Dict[str, float]) -> float:
        """Verify scroll behavior patterns"""
        try:
            current_features = self._extract_scroll_features(current_scroll)
            similarity = 0.0
            
            if 'avg_scroll_speed' in current_features and 'avg_scroll_speed' in stored_patterns:
                current_speed = current_features['avg_scroll_speed']
                stored_speed = stored_patterns['avg_scroll_speed']
                
                difference = abs(stored_speed - current_speed) / max(stored_speed, 1)
                if difference <= 0.4:
                    similarity += 1.0
            
            return min(similarity, 1.0)
            
        except Exception as e:
            logger.error(f"Scroll behavior verification failed: {str(e)}")
            return 0.0
    
    def _verify_browser_fingerprint(self, current_browser: Dict[str, Any], stored_fingerprint: Dict[str, Any]) -> float:
        """Verify browser fingerprint"""
        try:
            current_fingerprint = self._create_browser_fingerprint(current_browser)
            
            # Count matching attributes
            matching_attributes = 0
            total_attributes = len(stored_fingerprint)
            
            if total_attributes == 0:
                return 0.0
            
            for key, stored_value in stored_fingerprint.items():
                current_value = current_fingerprint.get(key)
                if current_value == stored_value:
                    matching_attributes += 1
            
            return matching_attributes / total_attributes
            
        except Exception as e:
            logger.error(f"Browser fingerprint verification failed: {str(e)}")
            return 0.0
    
    def _detect_web_anomalies(self, current_data: Dict[str, Any], stored_profile: Dict[str, Any]) -> List[str]:
        """Detect web-specific behavioral anomalies"""
        anomalies = []
        
        try:
            # Check for robotic mouse movements (too perfect)
            mouse_features = self._extract_mouse_features(current_data.get('mouse_movements', []))
            if 'mouse_speed_std' in mouse_features and mouse_features['mouse_speed_std'] < 0.1:
                anomalies.append('robotic_mouse_movements')
            
            # Check for inconsistent browser fingerprint
            browser_confidence = self._verify_browser_fingerprint(
                current_data.get('browser_info', {}),
                stored_profile.get('browser_fingerprint', {})
            )
            if browser_confidence < 0.3:
                anomalies.append('browser_fingerprint_mismatch')
            
        except Exception as e:
            logger.warning(f"Web anomaly detection failed: {str(e)}")
        
        return anomalies