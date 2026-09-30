import logging

from django.conf import settings
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView

from apps.common.api_spec import SECTION_TAGS
from apps.common.responses import success_response
from apps.common.throttling import EnvScopedRateThrottle

from .models import HirerMedia, HirerProfile, User
from .permissions import IsHirer, IsKaazbir
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    HirerBasicInfoSerializer,
    HirerMediaUploadSerializer,
    HirerProfilePictureSerializer,
    HirerRegisterSerializer,
    KaazbirProfileDetailSerializer,
    KaazbirProfileUpdateSerializer,
    KaazbirRegisterSerializer,
    KYCSubmitSerializer,
    LoginSerializer,
    NiyokdataProfileDetailSerializer,
    NiyokdataProfileUpdateSerializer,
    NotificationSettingsSerializer,
    ResendOTPSerializer,
    ResetPasswordSerializer,
    SwitchRoleSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from .services import AuthService, HirerProfileService, KaazbirProfileService

logger = logging.getLogger(__name__)

_hirer_media_item = inline_serializer(
    "HirerMediaItemResponse",
    fields={
        "name": serializers.CharField(),
        "picture": serializers.CharField(allow_null=True),
    },
)

_hirer_media_response = inline_serializer(
    "HirerMediaResponse",
    fields={
        "certificate": _hirer_media_item,
        "license": _hirer_media_item,
    },
)


def get_or_create_hirer_profile(user):
    profile, _ = HirerProfile.objects.get_or_create(user=user)
    return profile


class HirerRegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = None
    schema_skip_auth = True
    tags = [SECTION_TAGS["users-auth"]]
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
    tags = [SECTION_TAGS["users-auth"]]
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
    tags = [SECTION_TAGS["users-auth"]]
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
    throttle_classes = [EnvScopedRateThrottle]
    throttle_scope = "otp_resend"
    schema_skip_auth = True
    tags = [SECTION_TAGS["users-auth"]]
    request_serializer = ResendOTPSerializer
    response_serializer = inline_serializer(
        "ResendOTPResponse", fields={"message": serializers.CharField()}
    )

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


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [EnvScopedRateThrottle]
    throttle_scope = "password_reset"
    schema_skip_auth = True
    tags = [SECTION_TAGS["users-auth"]]
    request_serializer = ForgotPasswordSerializer
    response_serializer = inline_serializer(
        "ForgotPasswordResponse", fields={"message": serializers.CharField()}
    )

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        AuthService.request_password_reset(email)
        return success_response(
            message="If an account exists with this email, "
            "a password reset code has been sent.",
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = None
    schema_skip_auth = True
    tags = [SECTION_TAGS["users-auth"]]
    request_serializer = ResetPasswordSerializer
    response_serializer = inline_serializer(
        "ResetPasswordResponse", fields={"message": serializers.CharField()}
    )

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp_code = serializer.validated_data["otp_code"]
        new_password = serializer.validated_data["new_password"]
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
        otp_qs = user.otps.filter(purpose="password_reset", is_used=False).order_by(
            "-created_at"
        )
        latest_otp = otp_qs.first()
        if latest_otp and latest_otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            return Response(
                {
                    "success": False,
                    "error": {
                        "otp_code": "Maximum attempts exceeded. " "Request a new OTP."
                    },
                    "message": "Maximum attempts exceeded. Request a new OTP.",
                    "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        reset = AuthService.reset_password(email, otp_code, new_password)
        if not reset:
            return Response(
                {
                    "success": False,
                    "error": {"otp_code": "Invalid or expired OTP"},
                    "message": "Invalid or expired OTP",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            message="Password reset successfully.",
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [EnvScopedRateThrottle]
    throttle_scope = "login"
    schema_skip_auth = True
    tags = [SECTION_TAGS["users-auth"]]
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
    tags = [SECTION_TAGS["users-auth"]]
    request_serializer = inline_serializer(
        "LogoutBody",
        fields={"refresh": serializers.CharField(required=False)},
    )
    response_serializer = inline_serializer(
        "LogoutResponse", fields={"message": serializers.CharField()}
    )

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
    tags = [SECTION_TAGS["users-auth"]]
    response_serializer = UserSerializer

    def get(self, request):
        serializer = UserSerializer(request.user)
        return success_response(data=serializer.data)


class SwitchRoleView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [EnvScopedRateThrottle]
    throttle_scope = "role_switch"
    tags = [SECTION_TAGS["users-auth"]]
    request_serializer = SwitchRoleSerializer
    response_serializer = inline_serializer(
        "SwitchRoleResponse",
        fields={
            "access": serializers.CharField(),
            "refresh": serializers.CharField(),
            "user": UserSerializer(),
        },
    )

    def post(self, request):
        serializer = SwitchRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_role = serializer.validated_data["target_role"]
        if target_role == request.user.role:
            refresh = RefreshToken.for_user(request.user)
            return success_response(
                data={
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(request.user).data,
                },
                message="Role already active.",
            )
        try:
            user = AuthService.switch_active_role(
                request.user,
                target_role,
                phone_number=serializer.validated_data.get("phone_number"),
            )
        except ValueError as e:
            return Response(
                {
                    "success": False,
                    "error": {"target_role": [str(e)]},
                    "message": str(e),
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile_updates = {
            k: serializer.validated_data[k]
            for k in ("business_name", "service_category", "address")
            if serializer.validated_data.get(k)
        }
        if target_role == "kaazbir" and profile_updates:
            KaazbirProfileService.update_profile(user, profile_updates)
            user.refresh_from_db()
        refresh = RefreshToken.for_user(user)
        return success_response(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            message="Role switched successfully.",
        )


class KYCSubmitView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    tags = [SECTION_TAGS["kyc-verification"]]
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
    tags = [SECTION_TAGS["kaazbir-profiles"]]
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


class HirerBasicInfoView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    tags = [SECTION_TAGS["hirer-profiles"]]
    request_serializer = HirerBasicInfoSerializer
    response_serializer = inline_serializer(
        "HirerBasicInfoResponse",
        fields={
            "full_name": serializers.CharField(),
            "email": serializers.EmailField(),
            "phone_number": serializers.CharField(allow_null=True),
        },
    )

    def post(self, request):
        serializer = HirerBasicInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.full_name = serializer.validated_data["full_name"]
        user.email = serializer.validated_data["email"]
        if serializer.validated_data.get("phone_number"):
            from .validators import normalize_bd_phone

            user.phone_number = normalize_bd_phone(
                serializer.validated_data["phone_number"]
            )
        user.save(update_fields=["full_name", "email", "phone_number"])
        return success_response(
            data={
                "full_name": user.full_name,
                "email": user.email,
                "phone_number": user.phone_number,
            },
            message="Basic info updated successfully.",
        )


class HirerMediaView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    parser_classes = [MultiPartParser, FormParser]
    tags = [SECTION_TAGS["hirer-profiles"]]
    request_serializer = HirerMediaUploadSerializer
    response_serializer = _hirer_media_response

    def post(self, request):
        serializer = HirerMediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        data = {"certificate": None, "license": None}

        if serializer.validated_data.get("certificate_name"):
            cert = HirerMedia.objects.create(
                user=user,
                media_type=HirerMedia.MediaType.CERTIFICATE,
                name=serializer.validated_data["certificate_name"],
                picture=serializer.validated_data.get("certificate_picture"),
            )
            data["certificate"] = {
                "name": cert.name,
                "picture": (
                    request.build_absolute_uri(cert.picture.url)
                    if cert.picture
                    else None
                ),
            }

        if serializer.validated_data.get("license_name"):
            lic = HirerMedia.objects.create(
                user=user,
                media_type=HirerMedia.MediaType.LICENSE,
                name=serializer.validated_data["license_name"],
                picture=serializer.validated_data.get("license_picture"),
            )
            data["license"] = {
                "name": lic.name,
                "picture": (
                    request.build_absolute_uri(lic.picture.url) if lic.picture else None
                ),
            }

        return success_response(
            data=data,
            message="Media uploaded successfully.",
        )


class HirerProfilePictureView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    parser_classes = [MultiPartParser, FormParser]
    tags = [SECTION_TAGS["hirer-profiles"]]
    request_serializer = HirerProfilePictureSerializer
    response_serializer = inline_serializer(
        "HirerProfilePictureResponse",
        fields={"picture": serializers.CharField(allow_null=True)},
    )

    def post(self, request):
        serializer = HirerProfilePictureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = get_or_create_hirer_profile(request.user)
        profile.profile_picture = serializer.validated_data["picture"]
        profile.save(update_fields=["profile_picture"])
        return success_response(
            data={
                "picture": (
                    request.build_absolute_uri(profile.profile_picture.url)
                    if profile.profile_picture
                    else None
                ),
            },
            message="Profile picture updated successfully.",
        )


class HirerNotificationSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    tags = [SECTION_TAGS["hirer-profiles"]]
    request_serializer = NotificationSettingsSerializer
    response_serializer = NotificationSettingsSerializer

    def patch(self, request):
        profile = get_or_create_hirer_profile(request.user)
        serializer = NotificationSettingsSerializer(
            profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message="Notification settings updated successfully.",
        )


class HirerChangePasswordView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    tags = [SECTION_TAGS["users-auth"]]
    request_serializer = ChangePasswordSerializer
    response_serializer = inline_serializer(
        "PasswordChangeResponse", fields={"message": serializers.CharField()}
    )

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        if not user.check_password(serializer.validated_data["old_password"]):
            return success_response(
                data=None,
                message="Old password is incorrect.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return success_response(message="Password changed successfully.")


class NiyokdataProfileView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    tags = [SECTION_TAGS["hirer-profiles"]]
    response_serializer_get = NiyokdataProfileDetailSerializer
    request_serializer_post = NiyokdataProfileUpdateSerializer
    response_serializer_post = inline_serializer(
        "NiyokdataProfileUpdateResponse",
        fields={
            "id": serializers.UUIDField(),
            "is_profile_complete": serializers.BooleanField(),
        },
    )

    def get(self, request):
        profile = HirerProfileService.get_or_create_profile(request.user)
        serializer = NiyokdataProfileDetailSerializer(
            profile, context={"request": request}
        )
        return success_response(
            data=serializer.data,
            message="Profile fetched successfully.",
        )

    def post(self, request):
        serializer = NiyokdataProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = HirerProfileService.update_profile(
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
    tags = [SECTION_TAGS["users-auth"]]
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
