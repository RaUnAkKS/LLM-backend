from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User
from .serializers import (
    UserRegistrationSerializer, VerifyEmailSerializer,
    UserLoginSerializer, UserProfileSerializer,
    UserUpdateSerializer, ChangePasswordSerializer,
    SendOTPSerializer, VerifyPreRegistrationOTPSerializer
)


# ─── Step 1: Send OTP to email ────────────────────────────────────────────────
class SendOTPView(APIView):
    """
    POST /send-otp/
    User enters email → clicks "Send OTP" button
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.save()
        return Response(
            {"message": f"OTP sent to {email}. Please check your inbox."},
            status=status.HTTP_200_OK
        )


# ─── Step 2: Verify OTP ───────────────────────────────────────────────────────
class VerifyPreRegistrationOTPView(APIView):
    """
    POST /verify-otp/
    User enters OTP → clicks "Verify" button → email marked as verified
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyPreRegistrationOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.save()
        return Response(
            {"message": "Email verified! You can now complete your registration.", "email_verified": True},
            status=status.HTTP_200_OK
        )


# ─── Step 3: Complete Registration ────────────────────────────────────────────
class RegisterView(APIView):
    """
    POST /register/
    User fills full form → account created with is_verified=True already
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Registration successful! You can now log in."},
            status=status.HTTP_201_CREATED
        )



class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()   # marks is_verified=True, clears OTP

        return Response(
            {"message": f"Email verified successfully! Welcome, {user.username}. You can now log in."},
            status=status.HTTP_200_OK
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self,request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data,status=status.HTTP_200_OK)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,status=status.HTTP_200_OK)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        # Pass user as instance so serializer.validate() can call user.check_password()
        serializer = ChangePasswordSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)

class ForgotSendOTPView(APIView):
    """
    User enters email → clicks "Send OTP" button
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotSendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.save()
        return Response(
            {"message": f"OTP sent to {email}. Please check your inbox."},
            status=status.HTTP_200_OK
        )

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password changed successfully"},status=status.HTTP_200_OK)

class GoogleSignInView(APIView):
    """
    POST /auth/google/
    Frontend sends Google id_token → backend verifies → returns JWT
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleSignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = serializer.save()
        return Response(tokens, status=status.HTTP_200_OK)
