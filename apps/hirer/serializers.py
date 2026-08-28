from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from rest_framework import serializers

from .models import HirerMedia, HirerProfile


class HirerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HirerProfile
        fields = [
            "id",
            "profile_picture",
            "push_notifications",
            "sms_notifications",
            "email_notifications",
            "task_updates",
            "promotions_and_offers",
        ]


class HirerBasicInfoSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)


class HirerMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = HirerMedia
        fields = ["id", "media_type", "name", "picture"]


class HirerMediaUploadSerializer(serializers.Serializer):
    certificate_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    certificate_picture = serializers.ImageField(required=False)
    license_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    license_picture = serializers.ImageField(required=False)


class HirerProfilePictureSerializer(serializers.Serializer):
    picture = serializers.ImageField()


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = HirerProfile
        fields = [
            "push_notifications",
            "sms_notifications",
            "email_notifications",
            "task_updates",
            "promotions_and_offers",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(style={"input_type": "password"})
    new_password = serializers.CharField(style={"input_type": "password"})
    confirm_password = serializers.CharField(style={"input_type": "password"})

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except django_exceptions.ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, attrs):
        if attrs.get("new_password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs