import logging

from django.db import models, transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api_spec import SECTION_TAGS
from apps.common.responses import success_response
from apps.missions.models import Mission, MissionApplication, Review
from apps.users.permissions import IsKaazbir

from .serializers import (
    KaazbirActivityDetailSerializer,
    KaazbirActivitySerializer,
    KaazbirProfileDetailSerializer,
    KaazbirProfileUpdateSerializer,
    KYCSubmitSerializer,
    MissionBidSerializer,
    ReviewSerializer,
)
from .services import KaazbirProfileService

logger = logging.getLogger(__name__)


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


class KaazbirProfileCompletionView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    tags = [SECTION_TAGS["kaazbir-profiles"]]
    response_serializer = inline_serializer(
        "KaazbirProfileCompletionResponse",
        fields={
            "basic_info": serializers.BooleanField(),
            "available_service_time": serializers.BooleanField(),
            "service_location": serializers.BooleanField(),
            "kyc": serializers.BooleanField(),
        },
    )

    def get(self, request):
        return success_response(
            data=KaazbirProfileService.completion_checklist(request.user),
            message="Profile completion fetched successfully.",
        )


_kasbir_card_response = inline_serializer(
    "KasbirCardResponse",
    many=True,
    fields={
        "kasbir_id": serializers.UUIDField(),
        "name": serializers.CharField(),
        "profile_picture": serializers.CharField(allow_null=True),
        "hourly_rate": serializers.FloatField(allow_null=True),
        "completed_jobs": serializers.IntegerField(),
        "bio": serializers.CharField(allow_null=True),
        "rating": serializers.FloatField(allow_null=True),
    },
)


class MissionBidView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    tags = [SECTION_TAGS["missions-kaazbir"]]
    request_serializer = MissionBidSerializer
    response_serializer = inline_serializer(
        "MissionBidResponse",
        fields={
            "mission_id": serializers.UUIDField(),
            "status": serializers.CharField(),
        },
    )

    @transaction.atomic
    def post(self, request, pk):
        mission = Mission.objects.filter(pk=pk, status=Mission.Status.OPEN).first()
        if not mission:
            return success_response(
                data=None,
                message="Mission not found or no longer open.",
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = MissionBidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        budget = serializer.validated_data.get("budget")

        if action == "bid":
            mission.status = Mission.Status.INTERESTED
            mission.kasbir_bid_price = budget
            mission.save(update_fields=["status", "kasbir_bid_price"])

        MissionApplication.objects.update_or_create(
            mission=mission,
            kaazbir=request.user,
            defaults={
                "action": action,
                "budget": budget,
            },
        )

        return success_response(
            data={
                "mission_id": str(mission.id),
                "status": mission.status,
            },
            message="Bid submitted successfully.",
        )


class CategoryKasbirsView(APIView):
    permission_classes = [IsAuthenticated]
    tags = [SECTION_TAGS["kaazbir-profiles"]]
    response_serializer = inline_serializer(
        "CategoryKasbirResponse",
        many=True,
        fields={
            "kaazbir_id": serializers.UUIDField(),
            "name": serializers.CharField(),
            "profile_pic": serializers.CharField(allow_null=True),
            "rating_avg": serializers.FloatField(allow_null=True),
            "sub_categories": serializers.ListField(child=serializers.CharField()),
            "hourly_rate": serializers.FloatField(allow_null=True),
            "completed_jobs": serializers.IntegerField(),
            "bio": serializers.CharField(allow_null=True),
        },
    )

    def get(self, request, pk):
        from apps.users.models import User

        kaazbirs = (
            User.objects.filter(
                models.Q(role="kaazbir") | models.Q(kaazbir_profile__isnull=False),
                kasbir_services__service_id=pk,
                is_active=True,
            )
            .select_related("kaazbir_profile")
            .prefetch_related(
                "kasbir_services__subservices", "reviews_received", "missions_assigned"
            )
            .distinct()
        )

        data = []
        for k in kaazbirs:
            sub_categories = []
            for ks in k.kasbir_services.all():
                for sub in ks.subservices.all():
                    sub_categories.append(sub.name)

            reviews = k.reviews_received.all()
            avg_rating = (
                round(sum(r.rating for r in reviews) / reviews.count(), 1)
                if reviews
                else None
            )
            completed = k.missions_assigned.filter(status="completed").count()

            profile_pic_url = None
            if k.kaazbir_profile.profile_picture:
                profile_pic_url = request.build_absolute_uri(
                    k.kaazbir_profile.profile_picture.url
                )

            data.append(
                {
                    "kaazbir_id": str(k.id),
                    "name": k.full_name,
                    "profile_pic": profile_pic_url,
                    "rating_avg": avg_rating,
                    "sub_categories": sub_categories,
                    "hourly_rate": (
                        float(k.kaazbir_profile.hourly_rate)
                        if k.kaazbir_profile.hourly_rate
                        else None
                    ),
                    "completed_jobs": completed,
                    "bio": k.kaazbir_profile.bio,
                }
            )

        return success_response(data=data, message="Kasbirs fetched successfully.")


@extend_schema(
    tags=[SECTION_TAGS["kaazbir-profiles"]],
    parameters=[
        OpenApiParameter(
            "service_id", str, required=True, description="Service UUID (required)"
        ),
    ],
)
class KasbirListView(APIView):
    permission_classes = [IsAuthenticated]
    tags = [SECTION_TAGS["kaazbir-profiles"]]
    response_serializer = _kasbir_card_response

    def get(self, request):
        from apps.users.models import User

        service_id = request.query_params.get("service_id")
        if not service_id:
            return success_response(
                data=[],
                message="service_id is required.",
            )

        kaazbirs = (
            User.objects.filter(
                models.Q(role="kaazbir") | models.Q(kaazbir_profile__isnull=False),
                kasbir_services__service_id=service_id,
                is_active=True,
            )
            .select_related("kaazbir_profile")
            .prefetch_related("reviews_received", "missions_assigned")
            .distinct()
        )

        data = []
        for k in kaazbirs:
            reviews = k.reviews_received.all()
            avg_rating = (
                round(sum(r.rating for r in reviews) / reviews.count(), 1)
                if reviews
                else None
            )
            completed = k.missions_assigned.filter(status="completed").count()
            profile_pic_url = None
            if k.kaazbir_profile.profile_picture:
                profile_pic_url = request.build_absolute_uri(
                    k.kaazbir_profile.profile_picture.url
                )

            data.append(
                {
                    "kasbir_id": str(k.id),
                    "name": k.full_name,
                    "profile_picture": profile_pic_url,
                    "hourly_rate": (
                        float(k.kaazbir_profile.hourly_rate)
                        if k.kaazbir_profile.hourly_rate
                        else None
                    ),
                    "completed_jobs": completed,
                    "bio": k.kaazbir_profile.bio,
                    "rating": avg_rating,
                }
            )

        return success_response(data=data, message="Kasbirs fetched successfully.")


@extend_schema(
    tags=[SECTION_TAGS["kaazbir-profiles"]],
    parameters=[
        OpenApiParameter("service_id", str, description="Filter by service UUID"),
        OpenApiParameter("subservice_id", str, description="Filter by subservice UUID"),
        OpenApiParameter("location", str, description="Filter by location text"),
    ],
)
class KasbirAvailableView(APIView):
    permission_classes = [IsAuthenticated]
    tags = [SECTION_TAGS["kaazbir-profiles"]]
    response_serializer = _kasbir_card_response

    def get(self, request):
        from apps.users.models import User

        service_id = request.query_params.get("service_id")
        subservice_id = request.query_params.get("subservice_id")

        base_qs = (
            User.objects.filter(
                models.Q(role="kaazbir") | models.Q(kaazbir_profile__isnull=False),
                is_active=True,
            )
            .select_related("kaazbir_profile")
            .prefetch_related("reviews_received", "missions_assigned")
        )

        if service_id:
            base_qs = base_qs.filter(kasbir_services__service_id=service_id)

        if subservice_id:
            base_qs = base_qs.filter(kasbir_services__subservices__id=subservice_id)

        kaazbirs = base_qs.distinct()

        location = request.query_params.get("location")
        if location:
            kaazbirs = kaazbirs.filter(kaazbir_profile__location__icontains=location)

        data = []
        for k in kaazbirs:
            reviews = k.reviews_received.all()
            avg_rating = (
                round(sum(r.rating for r in reviews) / reviews.count(), 1)
                if reviews
                else None
            )
            completed = k.missions_assigned.filter(status="completed").count()
            profile_pic_url = None
            if k.kaazbir_profile.profile_picture:
                profile_pic_url = request.build_absolute_uri(
                    k.kaazbir_profile.profile_picture.url
                )

            data.append(
                {
                    "kasbir_id": str(k.id),
                    "name": k.full_name,
                    "profile_picture": profile_pic_url,
                    "hourly_rate": (
                        float(k.kaazbir_profile.hourly_rate)
                        if k.kaazbir_profile.hourly_rate
                        else None
                    ),
                    "completed_jobs": completed,
                    "bio": k.kaazbir_profile.bio,
                    "rating": avg_rating,
                }
            )

        return success_response(
            data=data, message="Available kasbirs fetched successfully."
        )


@extend_schema(
    tags=[SECTION_TAGS["kaazbir-profiles"]],
    parameters=[
        OpenApiParameter("service_id", str, description="Filter by service UUID"),
        OpenApiParameter("subservice_id", str, description="Filter by subservice UUID"),
        OpenApiParameter(
            "location",
            str,
            description="Search in location/district/division/upazila",
        ),
        OpenApiParameter("min_rating", float, description="Minimum average rating"),
        OpenApiParameter("max_rate", float, description="Max hourly rate"),
    ],
)
class KasbirSearchView(APIView):
    permission_classes = [IsAuthenticated]
    tags = [SECTION_TAGS["kaazbir-profiles"]]
    response_serializer = _kasbir_card_response

    def get(self, request):
        from apps.users.models import User

        service_id = request.query_params.get("service_id")
        subservice_id = request.query_params.get("subservice_id")
        location = request.query_params.get("location")
        min_rating = request.query_params.get("min_rating")
        max_rate = request.query_params.get("max_rate")

        base_qs = (
            User.objects.filter(
                models.Q(role="kaazbir") | models.Q(kaazbir_profile__isnull=False),
                is_active=True,
            )
            .select_related("kaazbir_profile")
            .prefetch_related("reviews_received", "missions_assigned")
        )

        if service_id:
            base_qs = base_qs.filter(kasbir_services__service_id=service_id)

        if subservice_id:
            base_qs = base_qs.filter(kasbir_services__subservices__id=subservice_id)

        if location:
            base_qs = base_qs.filter(
                models.Q(kaazbir_profile__location__icontains=location)
                | models.Q(kaazbir_profile__district__icontains=location)
                | models.Q(kaazbir_profile__division__icontains=location)
                | models.Q(kaazbir_profile__upazila__icontains=location)
            )

        if max_rate:
            base_qs = base_qs.filter(kaazbir_profile__hourly_rate__lte=max_rate)

        kaazbirs = base_qs.distinct()

        data = []
        for k in kaazbirs:
            reviews = k.reviews_received.all()
            avg_rating = (
                round(sum(r.rating for r in reviews) / reviews.count(), 1)
                if reviews
                else None
            )

            if min_rating and (avg_rating is None or avg_rating < float(min_rating)):
                continue

            completed = k.missions_assigned.filter(status="completed").count()
            profile_pic_url = None
            if k.kaazbir_profile.profile_picture:
                profile_pic_url = request.build_absolute_uri(
                    k.kaazbir_profile.profile_picture.url
                )

            data.append(
                {
                    "kasbir_id": str(k.id),
                    "name": k.full_name,
                    "profile_picture": profile_pic_url,
                    "hourly_rate": (
                        float(k.kaazbir_profile.hourly_rate)
                        if k.kaazbir_profile.hourly_rate
                        else None
                    ),
                    "completed_jobs": completed,
                    "bio": k.kaazbir_profile.bio,
                    "rating": avg_rating,
                }
            )

        return success_response(data=data, message="Kasbirs fetched successfully.")


@extend_schema(
    tags=[SECTION_TAGS["missions-kaazbir"]],
    parameters=[
        OpenApiParameter(
            "status",
            str,
            description="Filter: pending, upcoming, in_progress, completed",
        ),
    ],
)
class KaazbirActivityListView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    tags = [SECTION_TAGS["missions-kaazbir"]]
    response_serializer = KaazbirActivitySerializer
    response_many = True

    def get(self, request):
        status_filter = request.query_params.get("status")
        missions = (
            Mission.objects.filter(kaazbir=request.user)
            .select_related("service", "subservice")
            .prefetch_related("pictures")
            .order_by("-created_at")
        )

        if status_filter:
            status_map = {
                "pending": ["open", "interested", "offer_sent"],
                "upcoming": ["accepted"],
                "in_progress": ["in_progress"],
                "completed": ["completed"],
            }
            internal_statuses = status_map.get(status_filter, [])
            if internal_statuses:
                missions = missions.filter(status__in=internal_statuses)

        serializer = KaazbirActivitySerializer(
            missions, many=True, context={"request": request}
        )
        return success_response(
            data=serializer.data, message="Activities fetched successfully."
        )


class KaazbirActivityDetailView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    tags = [SECTION_TAGS["missions-kaazbir"]]
    response_serializer = KaazbirActivityDetailSerializer

    def get(self, request, pk):
        mission = (
            Mission.objects.filter(pk=pk, kaazbir=request.user)
            .select_related("hirer")
            .first()
        )
        if not mission:
            return success_response(
                data=None,
                message="Activity not found.",
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = KaazbirActivityDetailSerializer(
            mission, context={"request": request}
        )
        return success_response(
            data=serializer.data, message="Activity fetched successfully."
        )


@extend_schema(
    tags=[SECTION_TAGS["earnings-stats"]],
    parameters=[
        OpenApiParameter("range", str, description="weekly (default) or monthly"),
    ],
)
class KaazbirEarningsView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    tags = [SECTION_TAGS["earnings-stats"]]
    response_serializer = inline_serializer(
        "KaazbirEarningsResponse",
        fields={
            "range": serializers.CharField(),
            "data": serializers.ListField(
                child=inline_serializer(
                    "EarningBucketResponse",
                    fields={
                        "day": serializers.CharField(required=False),
                        "week": serializers.CharField(required=False),
                        "amount": serializers.FloatField(),
                    },
                )
            ),
        },
    )

    def get(self, request):
        from django.db.models import Sum
        from django.utils import timezone

        range_param = request.query_params.get("range", "weekly")
        queryset = Mission.objects.filter(
            kaazbir=request.user,
            status="completed",
            final_price__isnull=False,
        )

        now = timezone.now()
        data = []

        if range_param == "weekly":
            start_of_week = now - timezone.timedelta(days=now.weekday())
            for i in range(7):
                day = start_of_week + timezone.timedelta(days=i)
                day_total = (
                    queryset.filter(updated_at__date=day.date()).aggregate(
                        total=Sum("final_price")
                    )["total"]
                    or 0
                )
                data.append(
                    {
                        "day": day.strftime("%A"),
                        "amount": float(day_total),
                    }
                )
        elif range_param == "monthly":
            start_of_month = now.replace(day=1)
            for week in range(1, 5):
                week_start = start_of_month + timezone.timedelta(weeks=week - 1)
                week_end = week_start + timezone.timedelta(weeks=1)
                week_total = (
                    queryset.filter(
                        updated_at__gte=week_start,
                        updated_at__lt=week_end,
                    ).aggregate(total=Sum("final_price"))["total"]
                    or 0
                )
                data.append(
                    {
                        "week": f"Week {week}",
                        "amount": float(week_total),
                    }
                )

        return success_response(
            data={"range": range_param, "data": data},
            message="Earnings fetched successfully.",
        )


class KaazbirAcceptanceRatioView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    tags = [SECTION_TAGS["missions-kaazbir"]]
    response_serializer = inline_serializer(
        "AcceptanceRatioResponse",
        fields={
            "interested": serializers.IntegerField(),
            "accepted": serializers.IntegerField(),
            "declined": serializers.IntegerField(),
        },
    )

    def get(self, request):
        interested = Mission.objects.filter(
            kaazbir=request.user,
            status__in=["interested", "offer_sent"],
        ).count()
        accepted = Mission.objects.filter(
            kaazbir=request.user,
            status__in=["accepted", "in_progress", "completed"],
        ).count()
        declined = MissionApplication.objects.filter(
            kaazbir=request.user,
            action="reject",
        ).count()

        return success_response(
            data={
                "interested": interested,
                "accepted": accepted,
                "declined": declined,
            },
            message="Stats fetched successfully.",
        )


class KaazbirReviewAverageView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    tags = [SECTION_TAGS["reviews"]]
    response_serializer = inline_serializer(
        "ReviewAverageResponse",
        fields={
            "average_rating": serializers.FloatField(),
            "total_reviews": serializers.IntegerField(),
        },
    )

    def get(self, request):
        reviews = Review.objects.filter(kaazbir=request.user)
        total = reviews.count()
        avg = round(sum(r.rating for r in reviews) / total, 1) if total > 0 else 0
        return success_response(
            data={
                "average_rating": avg,
                "total_reviews": total,
            },
            message="Review stats fetched successfully.",
        )


class KaazbirReviewListView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    tags = [SECTION_TAGS["reviews"]]
    response_serializer = ReviewSerializer
    response_many = True

    def get(self, request):
        reviews = (
            Review.objects.filter(kaazbir=request.user)
            .select_related("hirer__hirer_profile")
            .order_by("-created_at")
        )

        serializer = ReviewSerializer(reviews, many=True, context={"request": request})
        return success_response(
            data=serializer.data, message="Reviews fetched successfully."
        )
