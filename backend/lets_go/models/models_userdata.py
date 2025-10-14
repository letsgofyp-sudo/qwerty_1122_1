from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator, ValidationError
from django.utils.translation import gettext_lazy as _

class UsersData(models.Model):
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(
        max_length=128,
        validators=[
            MinLengthValidator(8),
        ]
    )
    address = models.TextField()
    phone_no = models.CharField(
        max_length=16,  # allow for + and up to 15 digits
        validators=[
            RegexValidator(
                regex=r"^\+\d{10,15}$",
                message="Phone number must be in international format, e.g. +923001234567"
            )
        ]
    )
    cnic_no = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r"^\d{5}-\d{7}-\d{1}$",
                message="CNIC must be in the format 36603-0269853-9"
            )
        ]
    )
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female')]
    )
    driving_license_no = models.CharField(max_length=15, null=True, blank=True)
    accountno = models.CharField(max_length=20, null=True, blank=True)
    bankname = models.CharField(max_length=50, null=True, blank=True)
    profile_photo = models.BinaryField(null=True, blank=True)
    live_photo = models.BinaryField(null=True, blank=True)
    cnic_front_image = models.BinaryField(null=True, blank=True)
    cnic_back_image = models.BinaryField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        default='PENDING',
        choices=[
            ('PENDING', 'Pending'),
            ('VERIFIED', 'Verified'),
            ('REJECTED', 'Rejected'),
            ('BANNED', 'Banned'),
        ]
    )
    driving_license_front = models.BinaryField(null=True, blank=True)
    driving_license_back = models.BinaryField(null=True, blank=True)
    accountqr = models.BinaryField(null=True, blank=True)
    driver_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    passenger_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    fcm_token = models.TextField(null=True, blank=True, help_text='Firebase Cloud Messaging token for push notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Password complexity
        import re
        if self.password:
            if not re.search(r"[A-Z]", self.password):
                raise ValidationError({'password': _('Password must contain at least one uppercase letter.')})
            if not re.search(r"[a-z]", self.password):
                raise ValidationError({'password': _('Password must contain at least one lowercase letter.')})
            if not re.search(r"\d", self.password):
                raise ValidationError({'password': _('Password must contain at least one digit.')})
            if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", self.password):
                raise ValidationError({'password': _('Password must contain at least one special character.')})

        # If accountno is provided, bankname is required
        if self.accountno and not self.bankname:
            raise ValidationError({'bankname': _('Bank name is required if account number is provided.')})

        # If driving_license_no is provided, both images are required
        if self.driving_license_no:
            if not self.driving_license_front or not self.driving_license_back:
                raise ValidationError(_('Both front and back images of the driving license are required if license number is provided.'))

    def __str__(self):
        return self.name
