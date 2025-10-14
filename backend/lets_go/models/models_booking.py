from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

class Booking(models.Model):
    """Model for passenger bookings with multiple seats"""
    BOOKING_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    booking_id = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="Unique booking identifier like B001-2024-01-15-08:00-001"
    )
    trip = models.ForeignKey('Trip', on_delete=models.CASCADE, related_name='trip_bookings')
    passenger = models.ForeignKey('UsersData', on_delete=models.CASCADE, related_name='passenger_bookings')
    
    # Route details
    from_stop = models.ForeignKey(
        'RouteStop', 
        on_delete=models.CASCADE, 
        related_name='bookings_from',
        help_text="Pickup stop"
    )
    to_stop = models.ForeignKey(
        'RouteStop', 
        on_delete=models.CASCADE, 
        related_name='bookings_to',
        help_text="Drop-off stop"
    )
    
    # Seat details
    number_of_seats = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of seats booked"
    )
    seat_numbers = models.JSONField(
        default=list,
        help_text="Array of seat numbers booked"
    )
    
    # Fare details
    total_fare = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Total fare for all seats"
    )
    fare_breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed breakdown of fare calculation"
    )
    
    # Bargaining and negotiation fields
    original_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Original fare before negotiation"
    )
    negotiated_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final agreed fare after negotiation"
    )
    bargaining_status = models.CharField(
        max_length=20,
        choices=[
            ('NO_NEGOTIATION', 'No Negotiation'),
            ('PENDING', 'Pending Driver Response'),
            ('ACCEPTED', 'Accepted by Driver'),
            ('REJECTED', 'Rejected by Driver'),
            ('COUNTER_OFFER', 'Driver Counter Offer'),
        ],
        default='NO_NEGOTIATION',
        help_text="Current status of price negotiation"
    )
    passenger_offer = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Passenger's proposed fare"
    )
    driver_response = models.TextField(
        null=True,
        blank=True,
        help_text="Driver's response to passenger's offer"
    )
    negotiation_notes = models.TextField(
        null=True,
        blank=True,
        help_text="Additional notes about the negotiation"
    )
    
    # Status
    booking_status = models.CharField(
        max_length=20, 
        choices=BOOKING_STATUS_CHOICES, 
        default='PENDING'
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='PENDING'
    )
    
    # Passenger feedback
    passenger_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        null=True, 
        blank=True,
        help_text="Passenger rating (1.0 to 5.0)"
    )
    passenger_feedback = models.TextField(
        null=True, 
        blank=True,
        help_text="Passenger feedback about the trip"
    )
    
    # Timestamps
    booked_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['trip']),
            models.Index(fields=['passenger']),
            models.Index(fields=['booking_status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['booked_at']),
        ]
        ordering = ['-booked_at']

    def __str__(self):
        return f"Booking {self.booking_id}: {self.passenger.name} - {self.number_of_seats} seats"
    
    @property
    def seat_assignments(self):
        """Get all seat assignments for this booking"""
        return self.seat_assignments.all()
    
    @property
    def is_active(self):
        """Check if booking is active (confirmed)"""
        return self.booking_status == 'CONFIRMED'
    
    @property
    def can_cancel(self):
        """Check if booking can be cancelled"""
        return self.booking_status == 'CONFIRMED' and self.trip.trip_status == 'SCHEDULED'
    
    def clean(self):
        """Validate booking data"""
        if self.number_of_seats <= 0:
            raise ValidationError({'number_of_seats': 'Number of seats must be greater than 0.'})
        
        if self.total_fare <= 0:
            raise ValidationError({'total_fare': 'Total fare must be greater than 0.'})
        
        # Check if stops belong to the same route as trip
        if self.from_stop.route != self.trip.route or self.to_stop.route != self.trip.route:
            raise ValidationError('Both stops must belong to the same route as the trip.')
        
        # Check if pickup stop comes before drop-off stop
        if self.from_stop.stop_order >= self.to_stop.stop_order:
            raise ValidationError('Pickup stop must come before drop-off stop.')
        
        # Check if enough seats are available
        if self.trip.available_seats < self.number_of_seats:
            raise ValidationError(f'Only {self.trip.available_seats} seats available, but {self.number_of_seats} requested.')
    
    def save(self, *args, **kwargs):
        """Override save to update trip's available seats"""
        if self.pk is None:  # New booking
            # Only deduct seats if booking is confirmed, not for pending requests
            if self.booking_status == 'CONFIRMED':
                self.trip.available_seats -= self.number_of_seats
                self.trip.save()
                
                # Add passenger to chat group
                try:
                    self.trip.chat_group.add_member(self.passenger, 'PASSENGER')
                    self.trip.chat_group.send_system_message(f"👋 {self.passenger.name} joined the trip!")
                except:
                    pass  # Chat group might not exist yet
        
        super().save(*args, **kwargs)
    
    def cancel_booking(self, reason=None):
        """Cancel the booking"""
        if not self.can_cancel:
            raise ValidationError('This booking cannot be cancelled.')
        
        self.booking_status = 'CANCELLED'
        self.cancelled_at = timezone.now()
        self.save()
        
        # Update trip's available seats
        self.trip.available_seats += self.number_of_seats
        self.trip.save()
        
        # Remove from chat group
        try:
            self.trip.chat_group.remove_member(self.passenger)
            self.trip.chat_group.send_system_message(f"❌ {self.passenger.name} cancelled their booking")
        except:
            pass
    
    def complete_booking(self):
        """Mark booking as completed"""
        if self.booking_status != 'CONFIRMED':
            raise ValidationError('Only confirmed bookings can be completed.')
        
        self.booking_status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.save()
    
    def update_payment_status(self, status):
        """Update payment status"""
        if status not in dict(self.PAYMENT_STATUS_CHOICES):
            raise ValidationError('Invalid payment status.')
        
        self.payment_status = status
        self.save()

class SeatAssignment(models.Model):
    """Model for detailed seat management with passenger visibility"""
    trip = models.ForeignKey('Trip', on_delete=models.CASCADE, related_name='seat_assignments')
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='seat_assignments')
    seat_number = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Seat number (1, 2, 3, etc.)"
    )
    passenger = models.ForeignKey('UsersData', on_delete=models.CASCADE, related_name='seat_assignments')
    
    # Basic passenger info for other passengers to see
    passenger_name = models.CharField(
        max_length=100,
        help_text="Passenger name (for display to other passengers)"
    )
    passenger_phone = models.CharField(
        max_length=16, 
        null=True, 
        blank=True,
        help_text="Masked phone number (last 4 digits only)"
    )
    passenger_gender = models.CharField(
        max_length=10, 
        choices=[('male', 'Male'), ('female', 'Female')], 
        null=True, 
        blank=True,
        help_text="Passenger gender (for seat preferences)"
    )
    
    # Seat status
    is_occupied = models.BooleanField(
        default=False,
        help_text="Has passenger boarded?"
    )
    occupied_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When passenger boarded"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['trip', 'seat_number']
        indexes = [
            models.Index(fields=['trip']),
            models.Index(fields=['booking']),
            models.Index(fields=['passenger']),
            models.Index(fields=['is_occupied']),
        ]
        ordering = ['trip', 'seat_number']

    def __str__(self):
        return f"Seat {self.seat_number} - {self.passenger_name}"
    
    def clean(self):
        """Validate seat assignment data"""
        if self.seat_number <= 0:
            raise ValidationError({'seat_number': 'Seat number must be greater than 0.'})
        
        if self.seat_number > self.trip.total_seats:
            raise ValidationError({'seat_number': f'Seat number cannot exceed total seats ({self.trip.total_seats}).'})
        
        # Check if seat is already assigned to another booking
        if self.pk is None:  # New assignment
            if SeatAssignment.objects.filter(trip=self.trip, seat_number=self.seat_number).exists():
                raise ValidationError({'seat_number': f'Seat {self.seat_number} is already assigned.'})
    
    def mark_as_occupied(self):
        """Mark seat as occupied when passenger boards"""
        if not self.is_occupied:
            self.is_occupied = True
            self.occupied_at = timezone.now()
            self.save()
            
            # Send notification to chat
            try:
                self.trip.chat_group.send_system_message(f"✅ {self.passenger_name} has boarded (Seat {self.seat_number})")
            except:
                pass
    
    def mark_as_unoccupied(self):
        """Mark seat as unoccupied"""
        if self.is_occupied:
            self.is_occupied = False
            self.occupied_at = None
            self.save()
    
    def get_passenger_display_info(self):
        """Get passenger info for display to other passengers"""
        return {
            'name': self.passenger_name,
            'gender': self.passenger_gender,
            'phone': self.passenger_phone,
            'seat_number': self.seat_number,
            'is_occupied': self.is_occupied
        } 