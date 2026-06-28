import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import TimestampedModel

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True, db_index=True)
    email = models.EmailField(unique=True, null=True, blank=True, db_index=True)
    phone_number = models.CharField(
        max_length=20, unique=True, null=True, blank=True, db_index=True
    )
    full_name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=20,
        choices=[("hirer", "Hirer"), ("kaazbir", "KaazBir")],
        default="hirer",
    )
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(email__isnull=False)
                | models.Q(phone_number__isnull=False),
                name="user_has_email_or_phone",
            )
        ]

    def __str__(self):
        return self.username


def kyc_file_path(instance, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    return f"kyc/{instance.user_id}/{instance.document_type}/{filename}"


class KaazbirProfile(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="kaazbir_profile"
    )
    business_name = models.CharField(max_length=255)
    service_category = models.CharField(max_length=100)
    address = models.TextField()
    kyc_verified = models.BooleanField(default=False)

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
        User, on_delete=models.CASCADE, related_name="kyc_verification"
    )
    document_type = models.CharField(
        max_length=30, choices=DocumentType.choices
    )
    front_image = models.ImageField(upload_to=kyc_file_path)
    back_image = models.ImageField(upload_to=kyc_file_path)
    selfie_1 = models.ImageField(upload_to=kyc_file_path, blank=True, null=True)
    selfie_2 = models.ImageField(upload_to=kyc_file_path, blank=True, null=True)
    selfie_3 = models.ImageField(upload_to=kyc_file_path, blank=True, null=True)
    selfie_4 = models.ImageField(upload_to=kyc_file_path, blank=True, null=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    consent = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    def __str__(self):
        return f"KYC for {self.user.username} ({self.status})"


class OTP(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code_hash = models.CharField(max_length=255)
    purpose = models.CharField(
        max_length=30,
        choices=[("email_verification", "Email verification")],
        default="email_verification",
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP for {self.user.username} ({self.purpose})"
