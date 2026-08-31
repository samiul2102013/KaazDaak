import logging

from django.db import models, transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api_spec import SECTION_TAGS
from apps.common.pagination import StandardResultsPagination
from apps.common.responses import success_response
from apps.users.permissions import IsHirer, IsKaazbir

from .models import Mission, MissionApplication, Review
from .serializers import (
    HirerActivitySerializer,
    KaazbirActivityDetailSerializer,
    KaazbirActivitySerializer,
    MissionBidSerializer,
    MissionConfirmSerializer,
    MissionCreateSerializer,
    MissionListSerializer,
    MissionSerializer,
    ReviewSerializer,
)

logger = logging.getLogger(__name__)

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


class MissionCreateView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    parser_classes = [MultiPartParser, FormParser]
    tags = [SECTION_TAGS["missions-bids"]]
    request_serializer = MissionCreateSerializer
    response_serializer = {
        status.HTTP_201_CREATED: inline_serializer(
            "MissionCreateResponse",
            fields={
                "id": serializers.UUIDField(),
                "title": serializers.CharField(),
                "status": serializers.CharField(),
                "created_at": serializers.DateTimeField(),
                "mission": MissionSerializer(),
            },
        )
    }

    def post(self, request):
        serializer = MissionCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        mission = serializer.save()
        data = MissionSerializer(mission, context={"request": request}).data
        return success_response(
            data={
                "id": str(mission.id),
                "title": mission.title,
                "status": mission.status,
                "created_at": mission.created_at.isoformat(),
                "mission": data,
            },
            message="Mission created successfully.",
            status=status.HTTP_201_CREATED,
        )


class HirerRecentTasksView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    tags = [SECTION_TAGS["missions-bids"]]
    response_serializer = inline_serializer(
        "HirerRecentTaskResponse",
        many=True,
        fields={
            "mission_id": serializers.UUIDField(),
            "title": serializers.CharField(),
            "subtitle": serializers.CharField(allow_null=True),
            "amount": serializers.FloatField(),
            "posted_time_ago": serializers.CharField(),
            "total_applications": serializers.IntegerField(),
        },
    )

    def get(self, request):
        missions = (
            Mission.objects.filter(hirer=request.user)
            .prefetch_related("pictures")
            .order_by("-created_at")[:20]
        )
        from django.utils import timesince

        data = []
        for m in missions:
            data.append(
                {
                    "mission_id": str(m.id),
                    "title": m.title,
                    "subtitle": (
                        m.subtitle or m.description[:100] if m.description else ""
                    ),
                    "amount": float(m.budget) if m.budget else 0,
                    "posted_time_ago": timesince.timesince(m.created_at) + " ago",
                    "total_applications": m.applications.count(),
                }
            )
        return success_response(data=data, message="Recent tasks fetched successfully.")


@extend_schema(
    tags=[SECTION_TAGS["missions-bids"]],
    parameters=[
        OpenApiParameter("service_id", str, description="Filter by service UUID"),
        OpenApiParameter("subservice_id", str, description="Filter by subservice UUID"),
    ],
)
class MissionListView(APIView):
    permission_classes = [IsAuthenticated]
    tags = [SECTION_TAGS["missions-bids"]]
    response_serializer = inline_serializer(
        "PaginatedMissionFeedResponse",
        fields={
            "count": serializers.IntegerField(),
            "next": serializers.CharField(allow_null=True),
            "previous": serializers.CharField(allow_null=True),
            "results": MissionListSerializer(many=True),
        },
    )

    def get(self, request):
        queryset = (
            Mission.objects.filter(status=Mission.Status.OPEN)
            .select_related("hirer", "service", "subservice")
            .prefetch_related("pictures")
        )

        service_id = request.query_params.get("service_id")
        if service_id:
            queryset = queryset.filter(service_id=service_id)

        subservice_id = request.query_params.get("subservice_id")
        if subservice_id:
            queryset = queryset.filter(subservice_id=subservice_id)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = MissionListSerializer(
            page, many=True, context={"request": request}
        )
        paginated = paginator.get_paginated_response(serializer.data)
        return success_response(
            data=paginated.data, message="Missions fetched successfully."
        )


class MissionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    tags = [SECTION_TAGS["missions-bids"]]
    response_serializer = MissionSerializer

    def get(self, request, pk):
        mission = (
            Mission.objects.select_related("hirer", "kaazbir", "service", "subservice")
            .prefetch_related("pictures", "reviews")
            .get(pk=pk)
        )
        serializer = MissionSerializer(mission, context={"request": request})
        return success_response(
            data=serializer.data, message="Mission fetched successfully."
        )


class MissionBidView(APIView):
    permission_classes = [IsAuthenticated, IsKaazbir]
    tags = [SECTION_TAGS["missions-bids"]]
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


class MissionConfirmView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    tags = [SECTION_TAGS["missions-bids"]]
    request_serializer = MissionConfirmSerializer
    response_serializer = inline_serializer(
        "MissionConfirmResponse",
        fields={
            "mission_id": serializers.UUIDField(),
            "status": serializers.CharField(),
            "final_price": serializers.FloatField(allow_null=True),
            "payment_status": serializers.CharField(),
        },
    )

    @transaction.atomic
    def post(self, request, pk):
        mission = Mission.objects.filter(
            pk=pk,
            hirer=request.user,
            status__in=[Mission.Status.INTERESTED, Mission.Status.OFFER_SENT],
        ).first()
        if not mission:
            return success_response(
                data=None,
                message="Mission not found or cannot be confirmed.",
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = MissionConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kaazbir_id = serializer.validated_data["kaazbir_id"]
        mission.kaazbir_id = kaazbir_id
        mission.status = Mission.Status.ACCEPTED
        mission.final_price = mission.kasbir_bid_price or mission.budget
        mission.payment_status = Mission.PaymentStatus.HELD
        mission.save(
            update_fields=["kaazbir_id", "status", "final_price", "payment_status"]
        )

        return success_response(
            data={
                "mission_id": str(mission.id),
                "status": mission.status,
                "final_price": (
                    float(mission.final_price) if mission.final_price else None
                ),
                "payment_status": mission.payment_status,
            },
            message="Mission confirmed successfully.",
        )


class ChatOfferView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    tags = [SECTION_TAGS["missions-bids"]]
    request_serializer = inline_serializer(
        "ChatOfferBody",
        fields={
            "order_title": serializers.CharField(),
            "description": serializers.CharField(required=False, allow_blank=True),
            "budget": serializers.DecimalField(
                max_digits=10, decimal_places=2, required=False, allow_null=True
            ),
            "location": serializers.CharField(required=False, allow_blank=True),
            "work_location": serializers.CharField(required=False, allow_blank=True),
        },
    )
    response_serializer = {
        status.HTTP_201_CREATED: inline_serializer(
            "ChatOfferResponse",
            fields={
                "mission_id": serializers.UUIDField(),
                "status": serializers.CharField(),
            },
        )
    }

    @transaction.atomic
    def post(self, request, pk):
        from apps.users.models import User

        kaazbir = User.objects.filter(pk=pk, role="kaazbir").first()
        if not kaazbir:
            return success_response(
                data=None,
                message="Kaazbir not found.",
                status=status.HTTP_404_NOT_FOUND,
            )

        order_title = request.data.get("order_title")
        description = request.data.get("description", "")
        budget = request.data.get("budget")
        location = request.data.get("location", "")
        work_location = request.data.get("work_location", "")

        if not order_title:
            return success_response(
                data=None,
                message="order_title is required.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        mission = Mission.objects.create(
            title=order_title,
            description=description,
            budget=budget,
            location=location,
            delivery_location=work_location,
            hirer=request.user,
            kaazbir=kaazbir,
            origin=Mission.Origin.HIRER_DIRECT,
            status=Mission.Status.OFFER_SENT,
        )

        return success_response(
            data={
                "mission_id": str(mission.id),
                "status": mission.status,
            },
            message="Offer sent successfully.",
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=[SECTION_TAGS["missions-bids"]],
    parameters=[
        OpenApiParameter(
            "status",
            str,
            description="Filter: pending, hired, in_progress, completed, cancelled",
        ),
    ],
)
class HirerActivityView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    tags = [SECTION_TAGS["missions-bids"]]
    response_serializer = HirerActivitySerializer
    response_many = True

    def get(self, request):
        status_filter = request.query_params.get("status")
        missions = (
            Mission.objects.filter(hirer=request.user)
            .select_related("kaazbir")
            .prefetch_related("kaazbir__reviews_received")
            .order_by("-created_at")
        )

        if status_filter:
            status_map = {
                "pending": ["open", "interested", "offer_sent"],
                "hired": ["accepted"],
                "in_progress": ["in_progress"],
                "completed": ["completed"],
                "cancelled": ["cancelled", "rejected"],
            }
            internal_statuses = status_map.get(status_filter, [])
            if internal_statuses:
                missions = missions.filter(status__in=internal_statuses)

        serializer = HirerActivitySerializer(missions, many=True)
        return success_response(
            data=serializer.data, message="Activity fetched successfully."
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
                role="kaazbir",
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
                role="kaazbir",
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
            User.objects.filter(role="kaazbir", is_active=True)
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
            User.objects.filter(role="kaazbir", is_active=True)
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
    tags=[SECTION_TAGS["missions-bids"]],
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
    tags = [SECTION_TAGS["missions-bids"]]
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
    tags = [SECTION_TAGS["missions-bids"]]
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
    tags = [SECTION_TAGS["missions-bids"]]
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


class TaskMineView(APIView):
    permission_classes = [IsAuthenticated, IsHirer]
    tags = [SECTION_TAGS["missions-bids"]]
    response_serializer = inline_serializer(
        "TaskMineResponse",
        many=True,
        fields={
            "id": serializers.UUIDField(),
            "title": serializers.CharField(),
            "budget": serializers.FloatField(allow_null=True),
            "status": serializers.CharField(),
            "photos": serializers.ListField(child=serializers.CharField()),
            "created_at": serializers.DateTimeField(),
        },
    )

    def get(self, request):
        missions = (
            Mission.objects.filter(hirer=request.user)
            .prefetch_related("pictures")
            .order_by("-created_at")
        )

        data = []
        for m in missions:
            photos = []
            for pic in m.pictures.all():
                photos.append(request.build_absolute_uri(pic.image.url))

            data.append(
                {
                    "id": str(m.id),
                    "title": m.title,
                    "budget": float(m.budget) if m.budget else None,
                    "status": m.status,
                    "photos": photos,
                    "created_at": m.created_at.isoformat(),
                }
            )

        return success_response(data=data, message="Tasks fetched successfully.")
