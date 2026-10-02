from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from rest_framework import serializers

from apps.hirer.serializers import HirerProfileSerializer
from apps.kaazbir.serializers import KaazbirProfileSerializer

from .models import OTP, User
from .validators import canonical_bd_local, normalize_bd_phone, validate_bd_phone_number


class UserSerializer(serializers.ModelSerializer):
    kaazbir_profile = KaazbirProfileSerializer(read_only=True)
    hirer_profile = HirerProfileSerializer(read_only=True)
    roles = serializers.ListField(child=serializers.CharField(), read_only=True)
    active_role = serializers.CharField(source="role", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone_number",
            "full_name",
            "role",
            "roles",
            "active_role",
            "is_email_verified",
            "kaazbir_profile",
            "hirer_profile",
        ]


class HirerRegisterSerializer(serializers.Serializer):
    is_hirer = serializers.BooleanField(required=False, default=True)
    full_name = serializers.CharField(max_length=255, required=False)
    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_password(self, value):
        try:
            validate_password(value)
        except django_exceptions.ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return value.lower()

    def validate(self, attrs):
        if not attrs.get("is_hirer", True):
            raise serializers.ValidationError(
                {"is_hirer": "This endpoint creates hirer accounts."}
            )

        full_name = attrs.get("full_name") or attrs.get("name")
        if not full_name or not full_name.strip():
            raise serializers.ValidationError({"full_name": "This field is required."})
        attrs["full_name"] = full_name.strip()
        attrs.pop("name", None)
        attrs.pop("is_hirer", None)
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        attrs.pop("confirm_password")
        return attrs


class KaazbirRegisterSerializer(serializers.Serializer):
    is_kaazbir = serializers.BooleanField(required=False, default=True)
    full_name = serializers.CharField(max_length=255, required=False)
    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    business_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    service_category = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    address = serializers.CharField(required=False, allow_blank=True)

    def validate_password(self, value):
        try:
            validate_password(value)
        except django_exceptions.ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return value.lower()

    def validate_phone_number(self, value):
        local = canonical_bd_local(value)
        validate_bd_phone_number(local)
        if User.objects.filter(phone_number=normalize_bd_phone(local)).exists():
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )
        return value

    def validate(self, attrs):
        if not attrs.get("is_kaazbir", True):
            raise serializers.ValidationError(
                {"is_kaazbir": "This endpoint creates kaazbir accounts."}
            )
        full_name = attrs.get("full_name") or attrs.get("name")
        if not full_name or not full_name.strip():
            raise serializers.ValidationError({"full_name": "This field is required."})
        attrs["full_name"] = full_name.strip()
        attrs.pop("name", None)
        attrs.pop("is_kaazbir", None)
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        attrs.pop("confirm_password")
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6, min_length=6)

    def validate_email(self, value):
        return value.lower()


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_email(self, value):
        return value.lower()

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
        attrs.pop("confirm_password")
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(
        help_text="Email, username, or BD phone number.",
    )
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip()
        if not email:
            raise serializers.ValidationError({"email": "This field is required."})
        attrs["email"] = email
        return attrs


class SwitchRoleSerializer(serializers.Serializer):
    target_role = serializers.ChoiceField(choices=["hirer", "kaazbir"])
    phone_number = serializers.CharField(max_length=20, required=False)
    business_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    service_category = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    address = serializers.CharField(required=False, allow_blank=True)

    def validate_phone_number(self, value):
        local = canonical_bd_local(value)
        validate_bd_phone_number(local)
        return value


class OTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTP
        fields = "__all__"
