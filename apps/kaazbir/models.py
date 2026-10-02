import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


def kyc_file_path(instance, filename: str) -> str:
    return f"kyc/{instance.user_id}/{instance.document_type}/{filename}"


def kyc_selfie_file_path(instance, filename: str) -> str:
    return f"kyc/{instance.kyc.user_id}/{instance.kyc.document_type}/selfies/{filename}"


class KaazbirProfile(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kaazbir_profile",
    )
    business_name = models.CharField(max_length=255)
    service_category = models.CharField(max_length=100)
    address = models.TextField()
    kyc_verified = models.BooleanField(default=False)
    service_start_time = models.TimeField(null=True, blank=True)
    service_end_time = models.TimeField(null=True, blank=True)
    division = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    upazila = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    is_profile_complete = models.BooleanField(default=False)
    hourly_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(
        upload_to="kaazbir_profiles/", blank=True, null=True
    )

    def __str__(self):
        return f"{self.business_name} ({self.user.username})"


class KYCVerification(TimestampedModel):
    class DocumentType(models.TextChoices):
        NATIONAL_ID = "national_id", "National ID"
        PASSPORT = "passport", "Passport"
        DRIVING_LICENSE = "driving_license", "Driving License"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kyc_verification",
    )
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    front_image = models.ImageField(upload_to=kyc_file_path)
    back_image = models.ImageField(upload_to=kyc_file_path)
    extracted_data = models.JSONField(default=dict, blank=True)
    consent = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    def __str__(self):
        return f"KYC for {self.user.username} ({self.status})"


class KYCSelfie(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kyc = models.ForeignKey(
        KYCVerification, on_delete=models.CASCADE, related_name="selfies"
    )
    image = models.ImageField(upload_to=kyc_selfie_file_path)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Selfie {self.order} for {self.kyc.user.username}"
