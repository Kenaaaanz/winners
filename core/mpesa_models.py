"""
M-Pesa Transaction Models
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class MpesaTransaction(models.Model):
    """
    Model to track M-Pesa transactions
    """
    
    TRANSACTION_TYPES = [
        ('STK_PUSH', 'STK Push'),
        ('C2B', 'Customer to Business'),
        ('B2C', 'Business to Customer'),
        ('REVERSAL', 'Reversal'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('TIMEOUT', 'Timeout'),
    ]
    
    # Transaction details
    transaction_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    merchant_request_id = models.CharField(max_length=50, blank=True)
    checkout_request_id = models.CharField(max_length=50, blank=True)
    
    # Payment details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    account_reference = models.CharField(max_length=50)
    transaction_desc = models.CharField(max_length=100)
    
    # M-Pesa response
    mpesa_receipt_number = models.CharField(max_length=50, blank=True)
    result_code = models.IntegerField(null=True, blank=True)
    result_description = models.TextField(blank=True)
    response_code = models.CharField(max_length=10, blank=True)
    response_description = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    is_complete = models.BooleanField(default=False)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    raw_request = models.JSONField(null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Relations
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sale = models.ForeignKey('Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='mpesa_transactions')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['checkout_request_id']),
            models.Index(fields=['mpesa_receipt_number']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"MPesa {self.transaction_type} - {self.transaction_id}"
    
    def mark_success(self, receipt_number=None, result_code=None, result_desc=None):
        """Mark transaction as successful"""
        self.status = 'SUCCESS'
        self.is_complete = True
        self.completed_at = timezone.now()
        
        if receipt_number:
            self.mpesa_receipt_number = receipt_number
        if result_code:
            self.result_code = result_code
        if result_desc:
            self.result_description = result_desc
        
        self.save()
    
    def mark_failed(self, result_code=None, result_desc=None):
        """Mark transaction as failed"""
        self.status = 'FAILED'
        self.is_complete = True
        self.completed_at = timezone.now()
        
        if result_code:
            self.result_code = result_code
        if result_desc:
            self.result_description = result_desc
        
        self.save()
    
    def mark_cancelled(self):
        """Mark transaction as cancelled"""
        self.status = 'CANCELLED'
        self.is_complete = True
        self.completed_at = timezone.now()
        self.save()
    
    def to_dict(self):
        """Convert transaction to dictionary"""
        return {
            'transaction_id': self.transaction_id,
            'transaction_type': self.transaction_type,
            'amount': str(self.amount),
            'phone_number': self.phone_number,
            'account_reference': self.account_reference,
            'transaction_desc': self.transaction_desc,
            'status': self.status,
            'mpesa_receipt_number': self.mpesa_receipt_number,
            'result_code': self.result_code,
            'result_description': self.result_description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

class MpesaCallback(models.Model):
    """
    Model to store M-Pesa callback data for auditing
    """
    CALLBACK_TYPES = [
        ('STK', 'STK Push Callback'),
        ('C2B', 'C2B Validation/Confirmation'),
        ('B2C', 'B2C Result'),
        ('BALANCE', 'Balance Result'),
        ('REVERSAL', 'Reversal Result'),
        ('STATUS', 'Transaction Status Result'),
    ]
    
    callback_type = models.CharField(max_length=20, choices=CALLBACK_TYPES)
    transaction = models.ForeignKey(MpesaTransaction, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Callback data
    raw_data = models.JSONField()
    result_code = models.IntegerField(null=True, blank=True)
    result_description = models.TextField(blank=True)
    
    # Processing info
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_notes = models.TextField(blank=True)
    
    # Timestamps
    received_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['callback_type']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['received_at']),
        ]
    
    def __str__(self):
        return f"{self.callback_type} Callback - {self.received_at}"

class MpesaAccessToken(models.Model):
    """
    Model to cache M-Pesa access tokens
    """
    token = models.TextField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token expires at {self.expires_at}"
    
    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

class MpesaConfiguration(models.Model):
    """
    Model to store M-Pesa configuration
    """
    CONFIG_TYPES = [
        ('SANDBOX', 'Sandbox'),
        ('PRODUCTION', 'Production'),
    ]
    
    config_type = models.CharField(max_length=20, choices=CONFIG_TYPES, unique=True)
    consumer_key = models.CharField(max_length=200)
    consumer_secret = models.CharField(max_length=200)
    shortcode = models.CharField(max_length=20)
    passkey = models.TextField()
    initiator_name = models.CharField(max_length=100, blank=True)
    initiator_password = models.TextField(blank=True)
    certificate_path = models.CharField(max_length=500, blank=True)
    
    # URLs
    callback_base_url = models.URLField(blank=True)
    stk_callback_url = models.URLField(blank=True)
    c2b_validation_url = models.URLField(blank=True)
    c2b_confirmation_url = models.URLField(blank=True)
    
    # Settings
    is_active = models.BooleanField(default=False)
    auto_register_urls = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "M-Pesa Configuration"
        verbose_name_plural = "M-Pesa Configurations"
    
    def __str__(self):
        return f"{self.config_type} Configuration"
    
    def save(self, *args, **kwargs):
        # Ensure only one active configuration per type
        if self.is_active:
            MpesaConfiguration.objects.filter(
                config_type=self.config_type
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)