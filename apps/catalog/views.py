from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsPagination
from apps.common.responses import success_response

from .models import Campaign, Service
from .serializers import CampaignSerializer, ServiceSerializer


class ServiceListView(APIView):
    def get(self, request):
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(Service.objects.all(), request)
        serializer = ServiceSerializer(page, many=True, context={"request": request})
        return success_response(
            data=serializer.data, message="Services fetched successfully."
        )


class ServiceDetailView(APIView):
    def get(self, request, pk):
        service = get_object_or_404(Service, pk=pk)
        serializer = ServiceSerializer(service, context={"request": request})
        return success_response(
            data=serializer.data, message="Service fetched successfully."
        )


class CampaignListView(APIView):
    def get(self, request):
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(
            Campaign.objects.filter(is_active=True), request
        )
        serializer = CampaignSerializer(page, many=True, context={"request": request})
        return success_response(
            data=serializer.data, message="Campaigns fetched successfully."
        )
