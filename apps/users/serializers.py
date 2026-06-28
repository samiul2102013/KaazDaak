from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from rest_framework import serializers

from .models import OTP, KaazbirProfile, KYCVerification, User
from .validators import normalize_bd_phone, validate_bd_phone_number


class KaazbirProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = KaazbirProfile
        fields = ["business_name", "service_category", "address"]


class UserSerializer(serializers.ModelSerializer):
    kaazbir_profile = KaazbirProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone_number",
            "full_name",
            "role",
            "is_email_verified",
            "kaazbir_profile",
        ]


class HirerRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
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
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        attrs.pop("confirm_password")
        return attrs


class KaazbirRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
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
        validate_bd_phone_number(value)
        if User.objects.filter(phone_number=normalize_bd_phone(value)).exists():
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )
        return value

    def validate(self, attrs):
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


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})


class KYCSubmitSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(
        choices=["national_id", "passport", "driving_license"]
    )
    front_image = serializers.ImageField()
    back_image = serializers.ImageField()
    selfie_1 = serializers.ImageField(required=False)
    selfie_2 = serializers.ImageField(required=False)
    selfie_3 = serializers.ImageField(required=False)
    selfie_4 = serializers.ImageField(required=False)
    full_name = serializers.CharField(max_length=255)
    father_name = serializers.CharField(max_length=255)
    date_of_birth = serializers.CharField(max_length=20)
    address = serializers.CharField()
    post = serializers.CharField(max_length=100)
    thana = serializers.CharField(max_length=100)
    district = serializers.CharField(max_length=100)
    division = serializers.CharField(max_length=100)
    consent = serializers.BooleanField()

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError("Consent must be given.")
        return value

    def validate_front_image(self, value):
        validate_image_size(value)
        return value

    def validate_back_image(self, value):
        validate_image_size(value)
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        extracted_data = {
            "full_name": validated_data.pop("full_name"),
            "father_name": validated_data.pop("father_name"),
            "date_of_birth": validated_data.pop("date_of_birth"),
            "address": validated_data.pop("address"),
            "post": validated_data.pop("post"),
            "thana": validated_data.pop("thana"),
            "district": validated_data.pop("district"),
            "division": validated_data.pop("division"),
        }
        validated_data["extracted_data"] = extracted_data
        validated_data["user"] = user
        kyc = KYCVerification.objects.create(**validated_data)
        user.kaazbir_profile.kyc_verified = False
        user.kaazbir_profile.save(update_fields=["kyc_verified"])
        return kyc


def validate_image_size(image):
    max_size_mb = 5
    if image.size > max_size_mb * 1024 * 1024:
        raise serializers.ValidationError(
            f"Image size must not exceed {max_size_mb}MB."
        )


class OTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTP
        fields = "__all__"
