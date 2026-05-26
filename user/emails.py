from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_to_email(email):
    """
    Used on the REGISTER page:
    Creates/updates EmailVerification record, sends OTP.
    Returns the EmailVerification object.
    """
    from .models import EmailVerification

    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=10)  # OTP valid for 10 min

    # Update if exists, create if new
    verification, _ = EmailVerification.objects.update_or_create(
        email=email,
        defaults={
            'otp': otp,
            'is_verified': False,
            'expires_at': expires_at,
        }
    )

    subject = "Your Email Verification OTP"
    message = (
        f"Your OTP for email verification is: {otp}\n\n"
        f"This OTP expires in 10 minutes.\n"
        f"Do not share this with anyone."
    )
    send_mail(subject, message, settings.EMAIL_HOST_USER, [email])

    return verification


def send_otp_email(user):
    """
    Used AFTER registration (if re-verification needed).
    Saves OTP to User model and sends email.
    """
    otp = generate_otp()
    user.otp = otp
    user.save()

    subject = "Account recovery OTP"
    message = (
        f"Hello {user.username},\n\n"
        f"Your account recovery OTP is: {otp}\n\n"
        f"This OTP is valid for 10 minutes.\n"
        f"Do not share this with anyone.\n\n"
        f"— LLM Project Team"
    )
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])