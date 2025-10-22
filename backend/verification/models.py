from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import CustomUser

class IDVerification(models.Model):
    ID_TYPE_CHOICES = [
        ('nin', 'National ID Number (NIN)'),
        ('voters_card', "Voter's Card"),
        ('passport', 'International Passport'),
        ('drivers_license', "Driver's License"),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
        ('manual_review', 'Manual Review'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='id_verifications')
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES)
    id_number = models.CharField(max_length=100)
    id_image_front = models.ImageField(upload_to='id_documents/front/')
    id_image_back = models.ImageField(upload_to='id_documents/back/', null=True, blank=True)
    
    # OCR Extracted Data
    extracted_data = models.JSONField(default=dict)
    ocr_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0
    )
    
    # Verification Results
    government_verified = models.BooleanField(default=False)
    government_response = models.JSONField(default=dict)
    verification_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0
    )
    
    # Status Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    failure_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'id_verifications'
        verbose_name = 'ID Verification'
        verbose_name_plural = 'ID Verifications'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['id_type', 'id_number']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.id_type} - {self.status}"
    
    def mark_processing(self):
        self.status = 'processing'
        self.save()
    
    def mark_completed(self, verified=False, score=0.0, government_response=None):
        self.status = 'verified' if verified else 'failed'
        self.verification_score = score
        self.government_verified = verified
        self.government_response = government_response or {}
        self.completed_at = models.DateTimeField(auto_now=True)
        self.save()
        
        # Update user verification status if successful
        if verified and score >= 0.8:  # 80% confidence threshold
            self.user.upgrade_verification_tier(2)

class FacialVerification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='facial_verifications')
    id_verification = models.ForeignKey(IDVerification, on_delete=models.CASCADE, related_name='facial_checks')
    
    # Facial Images
    facial_image = models.ImageField(upload_to='facial_scans/')
    id_photo_extracted = models.TextField(blank=True)  # Base64 encoded ID photo
    
    # Verification Scores
    liveness_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0
    )
    match_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0
    )
    
    # Results
    liveness_passed = models.BooleanField(default=False)
    match_passed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Technical Details
    landmarks_detected = models.JSONField(default=list)  # Facial landmarks
    processing_time = models.FloatField(default=0.0)  # Processing time in seconds
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'facial_verifications'
        verbose_name = 'Facial Verification'
        verbose_name_plural = 'Facial Verifications'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['liveness_score']),
            models.Index(fields=['match_score']),
        ]
    
    def __str__(self):
        return f"Facial - {self.user.email} - {self.status}"
    
    def is_successful(self):
        return self.liveness_passed and self.match_passed and self.status == 'success'
    
    def calculate_overall_score(self):
        """Calculate overall facial verification score"""
        return (self.liveness_score * 0.4) + (self.match_score * 0.6)

class GovernmentVerificationLog(models.Model):
    VERIFICATION_TYPE_CHOICES = [
        ('nin', 'NIN Verification'),
        ('bvn', 'BVN Verification'),
        ('voters', "Voter's Card Verification"),
        ('passport', 'Passport Verification'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ]
    
    id_verification = models.ForeignKey(IDVerification, on_delete=models.CASCADE, related_name='gov_checks')
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPE_CHOICES)
    
    # Request/Response Data
    request_data = models.JSONField()
    response_data = models.JSONField()
    response_time = models.FloatField()  # In seconds
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'government_verification_logs'
        verbose_name = 'Government Verification Log'
        verbose_name_plural = 'Government Verification Logs'
        indexes = [
            models.Index(fields=['verification_type', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Gov Check - {self.verification_type} - {self.status}"

class VerificationSettings(models.Model):
    """Configuration for verification thresholds and settings"""
    name = models.CharField(max_length=100, unique=True)
    
    # OCR Settings
    ocr_confidence_threshold = models.FloatField(default=0.7)
    
    # Facial Recognition Settings
    liveness_threshold = models.FloatField(default=0.8)
    facial_match_threshold = models.FloatField(default=0.75)
    
    # Government API Settings
    gov_api_timeout = models.IntegerField(default=30)  # seconds
    max_retry_attempts = models.IntegerField(default=3)
    
    # General Settings
    auto_approval_enabled = models.BooleanField(default=True)
    manual_review_threshold = models.FloatField(default=0.6)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'verification_settings'
        verbose_name = 'Verification Setting'
        verbose_name_plural = 'Verification Settings'
    
    def __str__(self):
        return self.name