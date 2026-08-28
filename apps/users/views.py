import logging

from django.conf import settings
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView

from apps.common.responses import success_response

from .models import User
from .permissions import IsKaazbir
from .serializers import (
    HirerRegisterSerializer,
    KaazbirProfileDetailSerializer,
    KaazbirProfileUpdateSerializer,
    KaazbirRegisterSerializer,
    KYCSubmitSerializer,
    LoginSerializer,
    ResendOTPSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from .services import AuthService, KaazbirProfileService

logger = logging.getLogger(__name__)


class HirerRegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = None
    schema_skip_auth = True
    request_serializer = HirerRegisterSerializer
    response_serializer = {
        status.HTTP_201_CREATED: inline_serializer(
            "HirerRegisterResponse",
            fields={
                "user_id": serializers.UUIDField(),
                "username": serializers.CharField(),
                "email": serializers.EmailField(),
            },
        )
    }

    def post(self, request):
        serializer = HirerRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register_hirer(serializer.validated_data)
        return success_response(
            data={
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
            },
            message="Registration successful. Please verify your email.",
            status=status.HTTP_201_CREATED,
        )


class KaazbirRegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = None
    schema_skip_auth = True
    request_serializer = KaazbirRegisterSerializer
    response_serializer = {
        status.HTTP_201_CREATED: inline_serializer(
            "KaazbirRegisterResponse",
            fields={
                "user_id": serializers.UUIDField(),
                "username": serializers.CharField(),
                "email": serializers.EmailField(),
                "phone_number": serializers.CharField(allow_null=True),
            },
        )
    }

    def post(self, request):
        serializer = KaazbirRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register_kaazbir(serializer.validated_data)
        return success_response(
            data={
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
                "phone_number": user.phone_number,
            },
            message="Registration successful. Please verify your email.",
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = None
    schema_skip_auth = True
    request_serializer = VerifyEmailSerializer
    response_serializer = inline_serializer(
        "VerifyEmailResponse",
        fields={
            "access": serializers.CharField(),
            "refresh": serializers.CharField(),
        },
    )

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp_code = serializer.validated_data["otp_code"]
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {"otp_code": "Invalid or expired OTP"},
                    "message": "Invalid or expired OTP",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        otp_qs = user.otps.filter(purpose="email_verification", is_used=False).order_by(
            "-created_at"
        )
        latest_otp = otp_qs.first()
        if latest_otp and latest_otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            return Response(
                {
                    "success": False,
                    "error": {
                        "otp_code": "Maximum attempts exceeded. Request a new OTP."
                    },
                    "message": "Maximum attempts exceeded. Request a new OTP.",
                    "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        verified = AuthService.verify_otp(user, otp_code)
        if not verified:
            return Response(
                {
                    "success": False,
                    "error": {"otp_code": "Invalid or expired OTP"},
                    "message": "Invalid or expired OTP",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        refresh = RefreshToken.for_user(user)
        return success_response(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            message="Email verified successfully.",
        )


class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_resend"
    schema_skip_auth = True
    request_serializer = ResendOTPSerializer
    response_serializer = inline_serializer("ResendOTPResponse", fields={})

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return success_response(
                message="OTP resent successfully.",
            )
        if user.is_email_verified:
            return success_response(
                message="OTP resent successfully.",
            )
        AuthService.generate_and_send_otp(user)
        return success_response(
            message="OTP resent successfully.",
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
    schema_skip_auth = True
    request_serializer = LoginSerializer
    response_serializer = inline_serializer(
        "LoginResponse",
        fields={
            "access": serializers.CharField(),
            "refresh": serializers.CharField(),
            "user": UserSerializer(),
        },
    )

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]
        password = serializer.validated_data["password"]

        user = AuthService.authenticate_by_identifier(identifier, password)
        if user is None:
            return Response(
                {
                    "success": False,
                    "error": {"non_field_errors": ["Invalid credentials"]},
                    "message": "Invalid credentials",
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_email_verified:
            return Response(
                {
                    "success": False,
                    "error": {
                        "non_field_errors": [
                            "Email not verified. Please verify your email first."
                        ]
                    },
                    "message": "Email not verified. Please verify your email first.",
                    "status_code": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data
        return success_response(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data,
            },
            message="Login successful.",
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    request_serializer = inline_serializer(
        "LogoutRequest",
        fields={"refresh": serializers.CharField(required=False)},
    )
    response_serializer = inline_serializer("LogoutResponse", fields={})

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception as e:
            logger.warning("Logout failed for user %s: %s", request.user, str(e))
        return success_response(message="Logged out successfully.")


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    response_serializer = UserSerializer

    def get(self, request):
        serializer = UserSerializer(request.user)
        return success_response(data=serializer.data)


class KYCSubmitView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    request_serializer = KYCSubmitSerializer
    response_serializer = {
        status.HTTP_201_CREATED: inline_serializer(
            "KYCSubmitResponse",
            fields={
                "id": serializers.UUIDField(),
                "document_type": serializers.CharField(),
                "status": serializers.CharField(),
            },
        )
    }

    def post(self, request):
        serializer = KYCSubmitSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        kyc = serializer.save()
        return success_response(
            data={
                "id": str(kyc.id),
                "document_type": kyc.document_type,
                "status": kyc.status,
            },
            message="KYC submitted successfully.",
            status=status.HTTP_201_CREATED,
        )


class KaazbirProfileView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    response_serializer_get = KaazbirProfileDetailSerializer
    request_serializer_post = KaazbirProfileUpdateSerializer
    response_serializer_post = inline_serializer(
        "KaazbirProfileUpdateResponse",
        fields={
            "id": serializers.UUIDField(),
            "is_profile_complete": serializers.BooleanField(),
        },
    )

    def get(self, request):
        profile = KaazbirProfileService.get_or_create_profile(request.user)
        serializer = KaazbirProfileDetailSerializer(
            profile, context={"request": request}
        )
        return success_response(
            data=serializer.data,
            message="Profile fetched successfully.",
        )

    def post(self, request):
        serializer = KaazbirProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = KaazbirProfileService.update_profile(
            request.user, serializer.validated_data
        )
        return success_response(
            data={
                "id": str(profile.id),
                "is_profile_complete": profile.is_profile_complete,
            },
            message="Profile updated successfully.",
        )


class TokenRefreshView(SimpleJWTTokenRefreshView):
    schema_skip_auth = True
    request_serializer = TokenRefreshSerializer
    response_serializer = inline_serializer(
        "TokenRefreshResponse",
        fields={
            "access": serializers.CharField(),
            "refresh": serializers.CharField(),
        },
    )

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return success_response(
                data=response.data, message="Token refreshed successfully."
            )
        return response
