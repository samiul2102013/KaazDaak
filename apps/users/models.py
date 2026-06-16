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
        choices=[("general", "General"), ("provider", "Provider")],
        default="general",
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


class ProviderProfile(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="provider_profile"
    )
    business_name = models.CharField(max_length=255)
    service_category = models.CharField(max_length=100)
    address = models.TextField()

    def __str__(self):
        return f"{self.business_name} ({self.user.username})"


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
