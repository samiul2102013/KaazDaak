import logging

from django.db import transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.api_spec import SECTION_TAGS
from apps.common.pagination import StandardResultsPagination
from apps.common.responses import success_response
from apps.users.permissions import IsHirer

from .models import Mission
from .serializers import (
    HirerActivitySerializer,
    MissionConfirmSerializer,
    MissionCreateSerializer,
    MissionListSerializer,
    MissionSerializer,
)

logger = logging.getLogger(__name__)


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

        kaazbir = User.objects.filter(pk=pk).first()
        if not kaazbir or not kaazbir.has_role("kaazbir"):
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
