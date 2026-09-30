import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import TimestampedModel

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    ROLE_HIRER = "hirer"
    ROLE_KAAZBIR = "kaazbir"
    ROLE_CHOICES = [(ROLE_HIRER, "Hirer"), (ROLE_KAAZBIR, "KaazBir")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True, db_index=True)
    email = models.EmailField(unique=True, null=True, blank=True, db_index=True)
    phone_number = models.CharField(
        max_length=20, unique=True, null=True, blank=True, db_index=True
    )
    full_name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="Active role. One account can unlock both roles and "
        "switch between them; this field always holds the active one.",
    )
    roles = models.JSONField(
        default=list,
        blank=True,
        help_text="what is the role of the user? hirer or kaazbir?",
    )
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email__isnull=False)
                | models.Q(phone_number__isnull=False),
                name="user_has_email_or_phone",
            )
        ]

    def __str__(self):
        return self.username

    @property
    def active_role(self):
        return self.role

    def has_role(self, role):
        if self.role == role:
            return True
        try:
            return role in (self.roles or [])
        except TypeError:
            return False

    def unlock_role(self, role):
        roles = list(self.roles or [])
        if self.role and self.role not in roles:
            roles.append(self.role)
        if role not in roles:
            roles.append(role)
        self.roles = roles

    def switch_role(self, role):
        self.unlock_role(role)
        self.role = role


def kyc_file_path(instance, filename: str) -> str:
    return f"kyc/{instance.user_id}/{instance.document_type}/{filename}"


def kyc_selfie_file_path(instance, filename: str) -> str:
    return f"kyc/{instance.kyc.user_id}/{instance.kyc.document_type}/selfies/{filename}"


class KaazbirProfile(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="kaazbir_profile"
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
        User, on_delete=models.CASCADE, related_name="kyc_verification"
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


class HirerProfile(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="hirer_profile",
    )
    organization_name = models.CharField(max_length=255, blank=True, default="")
    address = models.TextField(blank=True, default="")
    division = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    upazila = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(blank=True, default="")
    is_profile_complete = models.BooleanField(default=False)
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
        User,
        on_delete=models.CASCADE,
        related_name="hirer_media",
    )
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    name = models.CharField(max_length=255)
    picture = models.ImageField(upload_to="hirer_media/")

    def __str__(self):
        return f"{self.user.username} - {self.media_type}: {self.name}"


class OTP(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code_hash = models.CharField(max_length=255)
    purpose = models.CharField(
        max_length=30,
        choices=[
            ("email_verification", "Email verification"),
            ("password_reset", "Password reset"),
        ],
        default="email_verification",
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP for {self.user.username} ({self.purpose})"
