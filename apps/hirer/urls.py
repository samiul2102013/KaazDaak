from django.urls import path

from .views import (
    HirerBasicInfoView,
    HirerChangePasswordView,
    HirerMediaView,
    HirerNotificationSettingsView,
    HirerProfilePictureView,
)

urlpatterns = [
    path("profile/basic-info/", HirerBasicInfoView.as_view(), name="hirer-basic-info"),
    path("profile/media/", HirerMediaView.as_view(), name="hirer-media"),
    path("profile/picture/", HirerProfilePictureView.as_view(), name="hirer-profile-picture"),
    path("settings/notifications/", HirerNotificationSettingsView.as_view(), name="hirer-notification-settings"),
    path("change-password/", HirerChangePasswordView.as_view(), name="hirer-change-password"),
]