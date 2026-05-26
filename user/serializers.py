from .models import *
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from .tasks import send_otp_to_email_task, send_otp_email_task   # ← Celery tasks

# ─── Step 1: User enters email → clicks "Send OTP" ───────────────────────────
class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, email):
        # Block if email is already a registered account
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("This email is already registered. Please login.")
        return email

    def save(self):
        email = self.validated_data['email']
        send_otp_to_email_task.delay(email)   # ← async: runs on 'email' queue
        return email


# ─── Step 2: User enters OTP → clicks "Verify" ───────────────────────────────
class VerifyPreRegistrationOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        email = data.get('email')
        otp = data.get('otp')

        try:
            verification = EmailVerification.objects.get(email=email)
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError("No OTP was sent to this email. Click 'Send OTP' first.")

        if verification.is_expired():
            raise serializers.ValidationError("OTP has expired. Please request a new one.")

        if verification.otp != otp:
            raise serializers.ValidationError("Invalid OTP. Please check your email.")

        self._verification = verification
        return data

    def save(self):
        # Mark this email as verified (pre-registration)
        self._verification.is_verified = True
        self._verification.save()
        return self._verification.email


# ─── Step 3: User fills rest of form → clicks "Register" ─────────────────────
class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        username = data.get('username')
        email = data.get('email')

        if password != confirm_password:
            raise serializers.ValidationError("Password and confirm password do not match")

        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError("Username already taken")

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("Email already registered")

        # Check email was pre-verified via OTP on this page
        try:
            verification = EmailVerification.objects.get(email=email)
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError("Please verify your email first using the OTP.")

        if not verification.is_verified:
            raise serializers.ValidationError("Email OTP not verified yet. Click 'Verify' button.")

        if verification.is_expired():
            raise serializers.ValidationError("OTP has expired. Please request a new OTP.")

        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        email = validated_data['email']

        # Create user — already email-verified, so set is_verified=True
        user = User.objects.create_user(
            username=validated_data['username'],
            email=email,
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            is_verified=True,   # ← pre-verified via OTP on register page
        )

        # Clean up the temporary verification record
        EmailVerification.objects.filter(email=email).delete()

        return user


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        email = data.get('email')
        otp = data.get('otp')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email")

        if user.is_verified:
            raise serializers.ValidationError("This account is already verified")

        if user.otp != otp:
            raise serializers.ValidationError("Invalid OTP. Please check your email")

        # Store user on serializer so save() can access it
        self.verified_user = user
        return data

    def save(self):
        # Mark user as verified and clear the OTP
        self.verified_user.is_verified = True
        self.verified_user.otp = ''       # clear OTP after use
        self.verified_user.save()
        return self.verified_user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        # authenticate() handles hashed password comparison correctly
        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_verified:
            raise serializers.ValidationError(
                "Email not verified. Please check your inbox for the OTP"
            )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "is_verified": user.is_verified,
            }
        }


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'is_verified', 'is_premium', 'created_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'full_name']   # don't allow email update here (security)

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        user = self.instance  # user passed from view

        # Check old password using Django's hashed check
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError("Old password is incorrect")

        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New password and confirm password do not match")

        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError("New password cannot be same as old password")

        return data

    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance

class ForgotSendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, email):
        # Single DB query — get user directly, not filter then get
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email")

        if not user.is_verified:
            raise serializers.ValidationError("Account is not verified. Cannot reset password.")

        self._user = user   # store for use in save()
        return email

    def save(self):
        send_otp_email_task.delay(str(self._user.id))   # ← async: runs on 'email' queue
        return self._user.email   # ← return EMAIL string, not user object!

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        email = data.get('email')
        otp = data.get('otp')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError("New password and confirm password do not match")

        # Single DB query — get directly instead of filter + get
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email")

        if not user.is_verified:
            raise serializers.ValidationError("Account is not verified")

        if user.otp != otp:
            raise serializers.ValidationError("Invalid OTP. Please check your email")

        self._user = user   # store so save() doesn't need another DB query
        return data

    def save(self):
        self._user.set_password(self.validated_data['new_password'])
        self._user.otp = ''    # clear OTP after use
        self._user.save()
        return self._user



class GoogleSignInSerializer(serializers.Serializer):
    id_token = serializers.CharField()   # token sent from frontend

    def validate(self, data):
        token = data.get('id_token')

        try:
            # Step 1: Verify the token with Google
            # Google checks: is this token genuine? is it for our app?
            google_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
        except ValueError as e:
            raise serializers.ValidationError(f"Invalid Google token: {str(e)}")

        # google_info now contains verified user data:
        # {
        #   "email": "ali@gmail.com",
        #   "name": "Ali Khan",
        #   "given_name": "Ali",
        #   "picture": "https://...",
        #   "email_verified": True,
        #   "sub": "1234567890"   ← Google's unique user ID
        # }

        if not google_info.get('email_verified'):
            raise serializers.ValidationError("Google email is not verified")

        self._google_info = google_info
        return data

    def save(self):
        info = self._google_info
        email = info['email']
        full_name = info.get('name', '')
        username = email.split('@')[0]   # use email prefix as username

        # Get existing user OR create new one
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'full_name': full_name,
                'is_verified': True,    # ← Google already verified the email
            }
        )

        if created:
            # New user via Google — set unusable password
            # (they sign in with Google, not password)
            user.set_unusable_password()
            user.save()

        # Generate JWT tokens for your app
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "is_new_user": created,     # frontend can show "Welcome!" if new
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
            }
        }

