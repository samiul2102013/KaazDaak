import logging

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api_spec import SECTION_TAGS
from apps.common.responses import success_response
from apps.users.permissions import IsHirer

from .models import HirerMedia, HirerProfile
from .serializers import (
    ChangePasswordSerializer,
    HirerBasicInfoSerializer,
    HirerMediaUploadSerializer,
    HirerProfilePictureSerializer,
    NotificationSettingsSerializer,
)

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
            from apps.users.validators import normalize_bd_phone

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
