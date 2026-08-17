from django.urls import path

from .views import CampaignListView, ServiceDetailView, ServiceListView

urlpatterns = [
    path("campaigns/", CampaignListView.as_view(), name="campaign-list"),
    path("services/", ServiceListView.as_view(), name="service-list"),
    path(
        "services/<uuid:pk>/",
        ServiceDetailView.as_view(),
        name="service-detail",
    ),
]
