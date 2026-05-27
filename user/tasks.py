from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random


def _generate_otp():
    return str(random.randint(100000, 999999))


# ─── Task 1: Pre-registration OTP (SendOTPView, ForgotSendOTPView) ────────────
@shared_task(
    bind=True,
    queue='email',
    max_retries=3,
    default_retry_delay=10,     # retry after 10s if SMTP fails
)
def send_otp_to_email_task(self, email):
    """
    Async version of send_otp_to_email().
    Creates EmailVerification record and sends OTP email in background.
    """
    try:
        from .models import EmailVerification

        otp = _generate_otp()
        expires_at = timezone.now() + timedelta(minutes=10)

        EmailVerification.objects.update_or_create(
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

    except Exception as exc:
        raise self.retry(exc=exc)


# ─── Task 2: Post-registration / Forgot Password OTP (User model) ─────────────
@shared_task(
    bind=True,
    queue='email',
    max_retries=3,
    default_retry_delay=10,
)
def send_otp_email_task(self, user_id):
    """
    Async version of send_otp_email().
    Generates OTP, saves to User.otp, sends email in background.
    """
    try:
        from .models import User

        user = User.objects.get(id=user_id)
        otp = _generate_otp()

        user.otp = otp
        user.save()

        subject = "Account Recovery OTP"
        message = (
            f"Hello {user.username},\n\n"
            f"Your account recovery OTP is: {otp}\n\n"
            f"This OTP is valid for 10 minutes.\n"
            f"Do not share this with anyone.\n\n"
            f"— LLM Project Team"
        )
        send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])

    except Exception as exc:
        raise self.retry(exc=exc)
