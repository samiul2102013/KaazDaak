from django.db import transaction
from rest_framework import serializers

from apps.catalog.models import Service, Subservice
from apps.users.models import User

from .models import Earning, Mission, MissionApplication, MissionPicture, Review


class MissionPictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissionPicture
        fields = ["id", "image"]


class MissionListSerializer(serializers.ModelSerializer):
    pictures = MissionPictureSerializer(many=True, read_only=True)
    posted_by = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            "id",
            "title",
            "subtitle",
            "budget",
            "location",
            "pictures",
            "status",
            "posted_by",
            "created_at",
        ]

    def get_posted_by(self, obj):
        return obj.hirer.full_name

    def get_subtitle(self, obj):
        return obj.subtitle or obj.description[:100] if obj.description else ""


class MissionCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    service_id = serializers.UUIDField()
    subservice_id = serializers.UUIDField()
    budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    location = serializers.CharField(required=False, allow_blank=True)
    delivery_location = serializers.CharField(required=False, allow_blank=True)
    custom_fields_data = serializers.JSONField(required=False, default=dict)
    pictures = serializers.ListField(
        child=serializers.ImageField(), required=False, allow_empty=True
    )

    def validate_service_id(self, value):
        if not Service.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Service does not exist.")
        return value

    def validate_subservice_id(self, value):
        if not Subservice.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Subservice does not exist.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        pictures = validated_data.pop("pictures", [])
        service_id = validated_data.pop("service_id")
        subservice_id = validated_data.pop("subservice_id")
        user = self.context["request"].user

        mission = Mission.objects.create(
            **validated_data,
            service_id=service_id,
            subservice_id=subservice_id,
            hirer=user,
            origin=Mission.Origin.HIRER_POSTED,
            status=Mission.Status.OPEN,
        )
        for image in pictures:
            MissionPicture.objects.create(mission=mission, image=image)

        return mission


class MissionSerializer(serializers.ModelSerializer):
    pictures = MissionPictureSerializer(many=True, read_only=True)
    service_name = serializers.SerializerMethodField()
    subservice_name = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            "id",
            "title",
            "subtitle",
            "description",
            "service",
            "subservice",
            "service_name",
            "subservice_name",
            "budget",
            "kasbir_bid_price",
            "final_price",
            "per_hour_rate",
            "pickup_location",
            "delivery_location",
            "location",
            "hirer",
            "kaazbir",
            "origin",
            "status",
            "payment_status",
            "delivery_time",
            "custom_fields_data",
            "pictures",
            "created_at",
            "updated_at",
        ]

    def get_service_name(self, obj):
        return obj.service.name if obj.service else None

    def get_subservice_name(self, obj):
        return obj.subservice.name if obj.subservice else None


class MissionApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissionApplication
        fields = [
            "id",
            "mission",
            "kaazbir",
            "action",
            "budget",
            "message",
            "created_at",
        ]
        read_only_fields = ["id", "mission", "kaazbir", "created_at"]


class MissionBidSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["bid", "reject"])
    budget = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )

    def validate(self, attrs):
        if attrs["action"] == "bid" and not attrs.get("budget"):
            raise serializers.ValidationError(
                {"budget": "Budget is required when bidding."}
            )
        return attrs


class MissionConfirmSerializer(serializers.Serializer):
    kaazbir_id = serializers.UUIDField()

    def validate_kaazbir_id(self, value):
        try:
            user = User.objects.get(pk=value, role="kaazbir")
        except User.DoesNotExist:
            raise serializers.ValidationError("Kaazbir not found.")
        return value


class HirerActivitySerializer(serializers.ModelSerializer):
    mission_id = serializers.UUIDField(source="id")
    amount = serializers.DecimalField(source="budget", max_digits=10, decimal_places=2)
    kasbir_name = serializers.SerializerMethodField()
    kasbir_rating = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            "mission_id",
            "title",
            "amount",
            "pickup_location",
            "delivery_location",
            "kasbir_name",
            "kasbir_rating",
            "display_status",
        ]

    def get_kasbir_name(self, obj):
        return obj.kaazbir.full_name if obj.kaazbir else None

    def get_kasbir_rating(self, obj):
        if obj.kaazbir:
            reviews = obj.kaazbir.reviews_received.all()
            if reviews:
                return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return None

    def get_display_status(self, obj):
        status_map = {
            "open": "pending",
            "interested": "pending",
            "offer_sent": "pending",
            "accepted": "hired",
            "in_progress": "in_progress",
            "completed": "completed",
            "cancelled": "cancelled",
            "rejected": "cancelled",
        }
        return status_map.get(obj.status, obj.status)


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
        except:
            pass
        return None


class EarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = Earning
        fields = ["id", "kaazbir", "mission", "amount", "created_at"]


class KasbirSearchSerializer(serializers.Serializer):
    kasbir_id = serializers.UUIDField(source="id")
    name = serializers.CharField(source="full_name")
    profile_picture = serializers.SerializerMethodField()
    hourly_rate = serializers.DecimalField(
        source="kaazbir_profile.hourly_rate",
        max_digits=10,
        decimal_places=2,
    )
    completed_jobs = serializers.SerializerMethodField()
    bio = serializers.CharField(source="kaazbir_profile.bio")
    rating = serializers.SerializerMethodField()

    class Meta:
        model = User

    def get_profile_picture(self, obj):
        try:
            if obj.kaazbir_profile.profile_picture:
                return self.context["request"].build_absolute_uri(
                    obj.kaazbir_profile.profile_picture.url
                )
        except:
            pass
        return None

    def get_completed_jobs(self, obj):
        return obj.missions_assigned.filter(status="completed").count()

    def get_rating(self, obj):
        reviews = obj.reviews_received.all()
        if reviews:
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return None
