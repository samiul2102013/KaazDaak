from django.urls import path

from .views import (
    CampaignListView,
    KaazbirServiceMineView,
    KaazbirServiceUpdateView,
    ServiceDetailView,
    ServiceListView,
)

urlpatterns = [
    path("campaigns/", CampaignListView.as_view(), name="campaign-list"),
    path("services/", ServiceListView.as_view(), name="service-list"),
    path(
        "services/<uuid:pk>/",
        ServiceDetailView.as_view(),
        name="service-detail",
    ),
    path(
        "kaazbir/services/mine/",
        KaazbirServiceMineView.as_view(),
        name="kaazbir-services-mine",
    ),
    path(
        "kaazbir/services/",
        KaazbirServiceUpdateView.as_view(),
        name="kaazbir-services-update",
    ),
]
