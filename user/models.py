from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=100)
    full_name = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    otp = models.CharField(max_length=6, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username


class EmailVerification(models.Model):
    """
    Temporary record created when user clicks "Send OTP" on the register page.
    Tracks whether an email was verified BEFORE account creation.
    Deleted after successful registration.
    """
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)   # True after OTP is confirmed
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()                # OTP expiry time

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.email} — {'verified' if self.is_verified else 'pending'}"