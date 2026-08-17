from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsPagination
from apps.common.responses import success_response

from .models import Campaign, Category
from .serializers import CampaignSerializer, CategorySerializer


class CategoryListView(APIView):
    def get(self, request):
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(Category.objects.all(), request)
        serializer = CategorySerializer(page, many=True, context={"request": request})
        return success_response(
            data=serializer.data, message="Categories fetched successfully."
        )


class CategoryDetailView(APIView):
    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, context={"request": request})
        return success_response(
            data=serializer.data, message="Category fetched successfully."
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
