from django.urls import path

from .views import CampaignListView, CategoryDetailView, CategoryListView

urlpatterns = [
    path("campaigns/", CampaignListView.as_view(), name="campaign-list"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path(
        "categories/<uuid:pk>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),
]
