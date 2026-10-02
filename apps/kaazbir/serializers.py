from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.serializers import KasbirServiceSerializer
from apps.missions.models import Mission, Review

from .models import KaazbirProfile, KYCSelfie, KYCVerification


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


class MissionBidSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["bid", "reject"])
    budget = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Required when 'action' is 'bid'.",
    )

    def validate(self, attrs):
        if attrs["action"] == "bid" and not attrs.get("budget"):
            raise serializers.ValidationError(
                {"budget": "Budget is required when bidding."}
            )
        return attrs


class KaazbirActivitySerializer(serializers.ModelSerializer):
    mission_id = serializers.UUIDField(source="id")
    category = serializers.SerializerMethodField()
    sub_category = serializers.SerializerMethodField()
    picture = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()
    amount = serializers.DecimalField(
        source="final_price", max_digits=10, decimal_places=2
    )

    class Meta:
        model = Mission
        fields = [
            "mission_id",
            "category",
            "sub_category",
            "picture",
            "title",
            "order_number",
            "amount",
            "pickup_location",
            "delivery_location",
            "status",
            "created_at",
        ]

    def get_category(self, obj):
        return obj.service.name if obj.service else None

    def get_sub_category(self, obj):
        return obj.subservice.name if obj.subservice else None

    def get_picture(self, obj):
        picture = obj.pictures.first()
        if picture:
            return self.context["request"].build_absolute_uri(picture.image.url)
        return None

    def get_order_number(self, obj):
        return f"ORD-{str(obj.id).upper()[:8]}"


class KaazbirActivityDetailSerializer(serializers.ModelSerializer):
    mission_id = serializers.UUIDField(source="id")
    order_number = serializers.SerializerMethodField()
    earning = serializers.DecimalField(
        source="final_price", max_digits=10, decimal_places=2
    )
    customer = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            "mission_id",
            "title",
            "created_at",
            "order_number",
            "earning",
            "pickup_location",
            "delivery_location",
            "customer",
        ]

    def get_order_number(self, obj):
        return f"ORD-{str(obj.id).upper()[:8]}"

    def get_customer(self, obj):
        return {
            "name": obj.hirer.full_name,
            "phone": obj.hirer.phone_number,
        }


class ReviewSerializer(serializers.ModelSerializer):
    hirer_name = serializers.SerializerMethodField()
    hirer_profile_pic = serializers.SerializerMethodField()
    review_time = serializers.DateTimeField(source="created_at")

    class Meta:
        model = Review
        fields = [
            "id",
            "hirer_name",
            "hirer_profile_pic",
            "review_time",
            "review_text",
            "rating",
        ]

    def get_hirer_name(self, obj):
        return obj.hirer.full_name

    def get_hirer_profile_pic(self, obj):
        try:
            profile = obj.hirer.hirer_profile
            if profile.profile_picture:
                return self.context["request"].build_absolute_uri(
                    profile.profile_picture.url
                )
        except AttributeError:
            pass
        return None
