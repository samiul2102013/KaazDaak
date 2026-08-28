from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.utils import extend_schema, inline_serializer
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.views import CampaignListView
from apps.users.views import KaazbirProfileView


@extend_schema(
    responses={
        200: inline_serializer(
            "HealthResponse",
            fields={
                "status": serializers.CharField(),
                "message": serializers.CharField(),
            },
        )
    }
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "healthy", "message": "KaazDaak API is online"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health_check"),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.missions.urls")),
    path("api/v1/hirer/", include("apps.hirer.urls")),
    path(
        "api/v1/kaazbir/profile/",
        KaazbirProfileView.as_view(),
        name="kaazbir-profile",
    ),
    path("api/v1/offers/", CampaignListView.as_view(), name="offers-list"),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="docs",
    ),
    path(
        "api/docs/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    try:
        import debug_toolbar

        urlpatterns += [
            path("__debug__/", include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
