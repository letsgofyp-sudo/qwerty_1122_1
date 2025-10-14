from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

class Route(models.Model):
    """Model for predefined bus/shuttle routes"""
    route_id = models.CharField(max_length=50, unique=True, help_text="Unique route identifier like R001")
    route_name = models.CharField(max_length=100, help_text="Display name for the route")
    route_description = models.TextField(null=True, blank=True, help_text="Detailed description of the route")
    total_distance_km = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0.1)],
        help_text="Total route distance in kilometers"
    )
    estimated_duration_minutes = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Estimated travel time in minutes"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this route is available for booking")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['route_id']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['route_name']

    def __str__(self):
        return f"Route {self.route_id}: {self.route_name}"
    
    @property
    def stops(self):
        """Get all stops in order"""
        return self.route_stops.all().order_by('stop_order')
    
    @property
    def first_stop(self):
        """Get first stop"""
        return self.stops.first()
    
    @property
    def last_stop(self):
        """Get last stop"""
        return self.stops.last()
    
    def clean(self):
        """Validate route data"""
        if self.total_distance_km and self.total_distance_km <= 0:
            raise ValidationError({'total_distance_km': 'Distance must be greater than 0.'})
        
        if self.estimated_duration_minutes and self.estimated_duration_minutes <= 0:
            raise ValidationError({'estimated_duration_minutes': 'Duration must be greater than 0.'})

class RouteStop(models.Model):
    """Model for stops along a route"""
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='route_stops')
    stop_name = models.CharField(max_length=100, help_text="Name of the stop")
    stop_order = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Order of this stop in the route (1, 2, 3, ...)"
    )
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        null=True, 
        blank=True,
        help_text="GPS latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        null=True, 
        blank=True,
        help_text="GPS longitude coordinate"
    )
    address = models.TextField(null=True, blank=True, help_text="Full address of the stop")
    estimated_time_from_start = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Estimated minutes from route start to this stop"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this stop is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['route', 'stop_order']
        indexes = [
            models.Index(fields=['route', 'stop_order']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['route', 'stop_order']

    def __str__(self):
        return f"{self.route.route_name} - Stop {self.stop_order}: {self.stop_name}"
    
    def clean(self):
        """Validate stop data"""
        if self.stop_order <= 0:
            raise ValidationError({'stop_order': 'Stop order must be greater than 0.'})
        
        if self.estimated_time_from_start and self.estimated_time_from_start < 0:
            raise ValidationError({'estimated_time_from_start': 'Time from start cannot be negative.'})
        
        # Check if stop order is unique within the route
        if self.pk is None:  # New instance
            if RouteStop.objects.filter(route=self.route, stop_order=self.stop_order).exists():
                raise ValidationError({'stop_order': f'Stop order {self.stop_order} already exists for this route.'})

class FareMatrix(models.Model):
    """Model for fare calculation between different stops"""
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='fare_matrix')
    from_stop = models.ForeignKey(
        RouteStop, 
        on_delete=models.CASCADE, 
        related_name='fare_from',
        help_text="Pickup stop"
    )
    to_stop = models.ForeignKey(
        RouteStop, 
        on_delete=models.CASCADE, 
        related_name='fare_to',
        help_text="Drop-off stop"
    )
    distance_km = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0.1)],
        help_text="Distance between stops in kilometers"
    )
    base_fare = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Standard fare for this route segment"
    )
    peak_fare = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Fare during peak hours (rush hour)"
    )
    off_peak_fare = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Fare during off-peak hours"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this fare is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['route', 'from_stop', 'to_stop']
        indexes = [
            models.Index(fields=['route']),
            models.Index(fields=['from_stop']),
            models.Index(fields=['to_stop']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.from_stop.stop_name} → {self.to_stop.stop_name}: ${self.base_fare}"
    
    def clean(self):
        """Validate fare matrix data"""
        if self.from_stop.route != self.route or self.to_stop.route != self.route:
            raise ValidationError('Both stops must belong to the same route.')
        
        if self.from_stop.stop_order >= self.to_stop.stop_order:
            raise ValidationError('Pickup stop must come before drop-off stop.')
        
        if self.distance_km <= 0:
            raise ValidationError({'distance_km': 'Distance must be greater than 0.'})
        
        if self.base_fare <= 0 or self.peak_fare <= 0 or self.off_peak_fare <= 0:
            raise ValidationError('All fares must be greater than 0.')
    
    def get_fare(self, is_peak_hour=False):
        """Get appropriate fare based on time"""
        if is_peak_hour:
            return self.peak_fare
        return self.off_peak_fare 