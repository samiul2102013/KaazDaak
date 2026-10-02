from django.urls import path

from .views import (
    CategoryKasbirsView,
    KaazbirAcceptanceRatioView,
    KaazbirActivityDetailView,
    KaazbirActivityListView,
    KaazbirEarningsView,
    KaazbirProfileCompletionView,
    KaazbirProfileView,
    KaazbirReviewAverageView,
    KaazbirReviewListView,
    KasbirAvailableView,
    KasbirListView,
    KasbirSearchView,
    MissionBidView,
)

urlpatterns = [
    path(
        "kaazbir/profile/",
        KaazbirProfileView.as_view(),
        name="kaazbir-profile",
    ),
    path(
        "kaazbir/profile-completion/",
        KaazbirProfileCompletionView.as_view(),
        name="kaazbir-profile-completion",
    ),
    path("missions/<uuid:pk>/bid/", MissionBidView.as_view(), name="mission-bid"),
    path("kasbir/", KasbirListView.as_view(), name="kasbir-list"),
    path("kasbir/available/", KasbirAvailableView.as_view(), name="kasbir-available"),
    path("kasbir/search/", KasbirSearchView.as_view(), name="kasbir-search"),
    path(
        "categories/<uuid:pk>/kasbirs/",
        CategoryKasbirsView.as_view(),
        name="category-kasbirs",
    ),
    path(
        "kaazbir/activities/",
        KaazbirActivityListView.as_view(),
        name="kaazbir-activities",
    ),
    path(
        "kaazbir/activities/<uuid:pk>/",
        KaazbirActivityDetailView.as_view(),
        name="kaazbir-activity-detail",
    ),
    path("kaazbir/earnings/", KaazbirEarningsView.as_view(), name="kaazbir-earnings"),
    path(
        "kaazbir/stats/acceptance-ratio/",
        KaazbirAcceptanceRatioView.as_view(),
        name="kaazbir-stats",
    ),
    path(
        "kaazbir/reviews/average/",
        KaazbirReviewAverageView.as_view(),
        name="kaazbir-reviews-avg",
    ),
    path("kaazbir/reviews/", KaazbirReviewListView.as_view(), name="kaazbir-reviews"),
]
