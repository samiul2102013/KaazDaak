from django.urls import path

from .views import (
    ChatOfferView,
    HirerActivityView,
    HirerRecentTasksView,
    MissionConfirmView,
    MissionCreateView,
    MissionDetailView,
    MissionListView,
    TaskMineView,
)

urlpatterns = [
    path("missions/", MissionCreateView.as_view(), name="mission-create"),
    path(
        "hirer/tasks/recent/", HirerRecentTasksView.as_view(), name="hirer-tasks-recent"
    ),
    path("hirer/activity/", HirerActivityView.as_view(), name="hirer-activity"),
    path("tasks/mine/", TaskMineView.as_view(), name="tasks-mine"),
    path("missions/<uuid:pk>/", MissionDetailView.as_view(), name="mission-detail"),
    path(
        "missions/<uuid:pk>/confirm/",
        MissionConfirmView.as_view(),
        name="mission-confirm",
    ),
    path("chat/<uuid:pk>/offers/", ChatOfferView.as_view(), name="chat-offers"),
    path("missions/feed/", MissionListView.as_view(), name="mission-feed"),
]
