from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.serializers import KasbirServiceSerializer

from .models import OTP, KaazbirProfile, KYCSelfie, KYCVerification, User
from .validators import normalize_bd_phone, validate_bd_phone_number


class KaazbirProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = KaazbirProfile
        fields = [
            "id",
            "business_name",
            "service_category",
            "address",
            "kyc_verified",
            "service_start_time",
            "service_end_time",
            "division",
            "district",
            "upazila",
            "location",
            "is_profile_complete",
        ]


class KaazbirProfileDetailSerializer(serializers.ModelSerializer):
    services = serializers.SerializerMethodField()

    class Meta:
        model = KaazbirProfile
        fields = [
            "id",
            "business_name",
            "service_category",
            "address",
            "kyc_verified",
            "service_start_time",
            "service_end_time",
            "division",
            "district",
            "upazila",
            "location",
            "is_profile_complete",
            "services",
        ]

    @extend_schema_field(field=KasbirServiceSerializer(many=True))
    def get_services(self, obj):
        from apps.catalog.serializers import KasbirServiceSerializer

        services = (
            obj.user.kasbir_services.all()
            .select_related("service")
            .prefetch_related("subservices")
        )
        return KasbirServiceSerializer(services, many=True, context=self.context).data


class KaazbirProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KaazbirProfile
        fields = [
            "business_name",
            "service_start_time",
            "service_end_time",
            "division",
            "district",
            "upazila",
            "location",
        ]


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
    identifier = serializers.CharField(
        required=False,
        help_text="Email, username, or BD phone number.",
    )
    email = serializers.EmailField(
        required=False,
        help_text="Alternative to 'identifier'. Email, username, or BD phone.",
    )
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        identifier = attrs.get("identifier") or attrs.get("email")
        if not identifier:
            raise serializers.ValidationError({"identifier": "This field is required."})
        attrs["identifier"] = identifier
        return attrs


class KYCSubmitSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(
        choices=["national_id", "passport", "driving_license"]
    )
    front_image = serializers.ImageField()
    back_image = serializers.ImageField()
    selfies = serializers.ListField(
        child=serializers.ImageField(), required=False, allow_empty=True
    )
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

    def validate_selfies(self, value):
        for image in value:
            validate_image_size(image)
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        selfies = validated_data.pop("selfies", [])
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
        for index, image in enumerate(selfies):
            KYCSelfie.objects.create(kyc=kyc, image=image, order=index)
        profile, _ = KaazbirProfile.objects.get_or_create(
            user=user,
            defaults={
                "business_name": extracted_data.get("full_name", ""),
                "service_category": "",
                "address": extracted_data.get("address", ""),
            },
        )
        profile.kyc_verified = False
        profile.save(update_fields=["kyc_verified"])
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
