import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class HirerProfile(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hirer_profile",
    )
    profile_picture = models.ImageField(
        upload_to="hirer_profiles/", blank=True, null=True
    )
    push_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    task_updates = models.BooleanField(default=True)
    promotions_and_offers = models.BooleanField(default=False)

    def __str__(self):
        return f"HirerProfile: {self.user.username}"


class HirerMedia(TimestampedModel):
    class MediaType(models.TextChoices):
        CERTIFICATE = "certificate", "Certificate"
        LICENSE = "license", "License"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hirer_media",
    )
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    name = models.CharField(max_length=255)
    picture = models.ImageField(upload_to="hirer_media/")

    def __str__(self):
        return f"{self.user.username} - {self.media_type}: {self.name}"