from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

class TripPayment(models.Model):
    """Model for individual booking payments"""
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('WALLET', 'Wallet'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHOD_CHOICES,
        help_text="Method used for payment"
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Payment amount"
    )
    transaction_id = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        unique=True,
        help_text="External transaction ID from payment gateway"
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='PENDING'
    )
    payment_gateway = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text="Payment gateway used (e.g., Stripe, PayPal)"
    )
    gateway_response = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Response from payment gateway"
    )
    
    # Payment details
    currency = models.CharField(
        max_length=3, 
        default='USD',
        help_text="Payment currency (USD, PKR, etc.)"
    )
    exchange_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=6,
        default=1.0,
        help_text="Exchange rate if different from base currency"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional info
    notes = models.TextField(null=True, blank=True, help_text="Additional payment notes")
    receipt_url = models.URLField(null=True, blank=True, help_text="URL to payment receipt")

    class Meta:
        indexes = [
            models.Index(fields=['booking']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.transaction_id or self.id} for Booking {self.booking.booking_id}"
    
    @property
    def is_successful(self):
        """Check if payment was successful"""
        return self.payment_status == 'COMPLETED'
    
    @property
    def is_pending(self):
        """Check if payment is pending"""
        return self.payment_status == 'PENDING'
    
    @property
    def is_failed(self):
        """Check if payment failed"""
        return self.payment_status == 'FAILED'
    
    @property
    def is_refunded(self):
        """Check if payment was refunded"""
        return self.payment_status == 'REFUNDED'
    
    def clean(self):
        """Validate payment data"""
        if self.amount <= 0:
            raise ValidationError({'amount': 'Payment amount must be greater than 0.'})
        
        if self.exchange_rate <= 0:
            raise ValidationError({'exchange_rate': 'Exchange rate must be greater than 0.'})
    
    def mark_as_completed(self, transaction_id=None, gateway_response=None):
        """Mark payment as completed"""
        if self.payment_status != 'PENDING':
            raise ValidationError('Only pending payments can be marked as completed.')
        
        self.payment_status = 'COMPLETED'
        self.completed_at = timezone.now()
        
        if transaction_id:
            self.transaction_id = transaction_id
        
        if gateway_response:
            self.gateway_response = gateway_response
        
        self.save()
        
        # Update booking payment status
        self.booking.update_payment_status('COMPLETED')
    
    def mark_as_failed(self, gateway_response=None):
        """Mark payment as failed"""
        if self.payment_status not in ['PENDING', 'COMPLETED']:
            raise ValidationError('Only pending or completed payments can be marked as failed.')
        
        self.payment_status = 'FAILED'
        self.failed_at = timezone.now()
        
        if gateway_response:
            self.gateway_response = gateway_response
        
        self.save()
        
        # Update booking payment status
        self.booking.update_payment_status('FAILED')
    
    def mark_as_refunded(self, refund_amount=None, gateway_response=None):
        """Mark payment as refunded"""
        if self.payment_status != 'COMPLETED':
            raise ValidationError('Only completed payments can be refunded.')
        
        self.payment_status = 'REFUNDED'
        self.refunded_at = timezone.now()
        
        if refund_amount:
            self.amount = refund_amount
        
        if gateway_response:
            self.gateway_response = gateway_response
        
        self.save()
        
        # Update booking payment status
        self.booking.update_payment_status('REFUNDED')
    
    def get_payment_summary(self):
        """Get payment summary for display"""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'receipt_url': self.receipt_url,
        }

class PaymentRefund(models.Model):
    """Model for payment refunds"""
    REFUND_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSED', 'Processed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    REFUND_REASON_CHOICES = [
        ('TRIP_CANCELLED', 'Trip Cancelled'),
        ('PASSENGER_REQUEST', 'Passenger Request'),
        ('DUPLICATE_PAYMENT', 'Duplicate Payment'),
        ('TECHNICAL_ISSUE', 'Technical Issue'),
        ('OTHER', 'Other'),
    ]
    
    original_payment = models.ForeignKey(
        TripPayment, 
        on_delete=models.CASCADE, 
        related_name='refunds',
        help_text="Original payment being refunded"
    )
    refund_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Amount to be refunded"
    )
    refund_reason = models.CharField(
        max_length=20, 
        choices=REFUND_REASON_CHOICES,
        help_text="Reason for refund"
    )
    refund_status = models.CharField(
        max_length=20, 
        choices=REFUND_STATUS_CHOICES, 
        default='PENDING'
    )
    
    # Refund details
    refund_method = models.CharField(
        max_length=20, 
        choices=TripPayment.PAYMENT_METHOD_CHOICES,
        help_text="Method used for refund"
    )
    refund_transaction_id = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text="External refund transaction ID"
    )
    gateway_response = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Response from payment gateway for refund"
    )
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional info
    requested_by = models.ForeignKey(
        'UsersData', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="User who requested the refund"
    )
    notes = models.TextField(null=True, blank=True, help_text="Additional refund notes")

    class Meta:
        indexes = [
            models.Index(fields=['original_payment']),
            models.Index(fields=['refund_status']),
            models.Index(fields=['requested_at']),
        ]
        ordering = ['-requested_at']

    def __str__(self):
        return f"Refund {self.id} for Payment {self.original_payment.id}"
    
    def clean(self):
        """Validate refund data"""
        if self.refund_amount <= 0:
            raise ValidationError({'refund_amount': 'Refund amount must be greater than 0.'})
        
        if self.refund_amount > self.original_payment.amount:
            raise ValidationError({'refund_amount': 'Refund amount cannot exceed original payment amount.'})
    
    def process_refund(self, refund_transaction_id=None, gateway_response=None):
        """Process the refund"""
        if self.refund_status != 'PENDING':
            raise ValidationError('Only pending refunds can be processed.')
        
        self.refund_status = 'PROCESSED'
        self.processed_at = timezone.now()
        
        if refund_transaction_id:
            self.refund_transaction_id = refund_transaction_id
        
        if gateway_response:
            self.gateway_response = gateway_response
        
        self.save()
        
        # Mark original payment as refunded
        self.original_payment.mark_as_refunded(self.refund_amount, gateway_response)
    
    def mark_as_failed(self, gateway_response=None):
        """Mark refund as failed"""
        if self.refund_status != 'PENDING':
            raise ValidationError('Only pending refunds can be marked as failed.')
        
        self.refund_status = 'FAILED'
        self.failed_at = timezone.now()
        
        if gateway_response:
            self.gateway_response = gateway_response 