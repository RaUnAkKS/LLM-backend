from django.urls import path
from .views import *

urlpatterns = [
    # ── Pre-registration email verification (shown on register page) ──
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),                   # Step 1: Enter email → Send OTP
    path('verify-otp/', VerifyPreRegistrationOTPView.as_view(), name='verify-otp'),  # Step 2: Enter OTP → Verify

    # ── Registration & Auth ───────────────────────────────────────────
    path('register/', RegisterView.as_view(), name='register'),                  # Step 3: Fill form → Create account
    path('login/', LoginView.as_view(), name='login'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),       # Legacy post-registration verify

    # ── Profile ──────────────────────────────────────────────────────
    path('profile/', ProfileView.as_view(), name='profile'),
    path('update-profile/', UpdateProfileView.as_view(), name='update-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),

    # ── Forgot Password ───────────────────────────────────────────────
    path('forgot-send-otp/', ForgotSendOTPView.as_view(), name='forgot-send-otp'),   # Step 1: Send OTP
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),  # Step 2: Reset password

    # ── Google Sign In ───────────────────────────────────────────────
    path('auth/google/', GoogleSignInView.as_view(), name='google-signin'),
]

