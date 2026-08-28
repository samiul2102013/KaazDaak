from django.shortcuts import get_object_or_404
from drf_spectacular.utils import inline_serializer
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsPagination
from apps.common.responses import success_response
from apps.users.permissions import IsKaazbir

from .models import Campaign, Service, Subservice
from .serializers import (
    CampaignSerializer,
    KaazbirServiceUpdateSerializer,
    KasbirServiceSerializer,
    ServiceSerializer,
    SubserviceCustomFieldSerializer,
)
from .services import KaazbirServiceService


class ServiceListView(APIView):
    tags = ["Catalog"]
    response_serializer = ServiceSerializer
    response_many = True

    def get(self, request):
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(Service.objects.all(), request)
        serializer = ServiceSerializer(page, many=True, context={"request": request})
        return success_response(
            data=serializer.data, message="Services fetched successfully."
        )


class ServiceDetailView(APIView):
    tags = ["Catalog"]
    response_serializer = ServiceSerializer

    def get(self, request, pk):
        service = get_object_or_404(Service, pk=pk)
        serializer = ServiceSerializer(service, context={"request": request})
        return success_response(
            data=serializer.data, message="Service fetched successfully."
        )


class CampaignListView(APIView):
    schema_skip_auth = True
    tags = ["Catalog"]
    response_serializer = CampaignSerializer
    response_many = True

    def get(self, request):
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(
            Campaign.objects.filter(is_active=True), request
        )
        serializer = CampaignSerializer(page, many=True, context={"request": request})
        return success_response(
            data=serializer.data, message="Campaigns fetched successfully."
        )


class KaazbirServiceUpdateView(APIView):
    permission_classes = [IsKaazbir]
    tags = ["Catalog"]
    request_serializer = KaazbirServiceUpdateSerializer
    response_serializer = inline_serializer(
        "KaazbirServiceUpdateResponse",
        fields={"services": KasbirServiceSerializer(many=True)},
    )

    def post(self, request):
        serializer = KaazbirServiceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entries = serializer.validated_data["services"]
        KaazbirServiceService.replace_services(request.user, entries)
        services = (
            request.user.kasbir_services.all()
            .select_related("service")
            .prefetch_related("subservices")
        )
        data = KasbirServiceSerializer(
            services, many=True, context={"request": request}
        ).data
        return success_response(
            data={"services": data},
            message="Services updated successfully.",
        )


class KaazbirServiceMineView(APIView):
    permission_classes = [IsKaazbir]
    tags = ["Catalog"]
    response_serializer = inline_serializer(
        "KasbirServicesResponse",
        fields={"services": KasbirServiceSerializer(many=True)},
    )

    def get(self, request):
        services = (
            request.user.kasbir_services.all()
            .select_related("service")
            .prefetch_related("subservices")
        )
        data = KasbirServiceSerializer(
            services, many=True, context={"request": request}
        ).data
        return success_response(
            data={"services": data},
            message="Services fetched successfully.",
        )


class SubserviceCustomFieldsView(APIView):
    permission_classes = [AllowAny]
    schema_skip_auth = True
    tags = ["Catalog"]
    response_serializer = SubserviceCustomFieldSerializer
    response_many = True

    def get(self, request, pk):
        subservice = get_object_or_404(Subservice, pk=pk)
        configs = subservice.custom_field_configs.select_related(
            "custom_field"
        ).order_by("order", "id")
        serializer = SubserviceCustomFieldSerializer(
            configs, many=True, context={"request": request}
        )
        return success_response(
            data=serializer.data,
            message="Custom fields fetched successfully.",
        )
