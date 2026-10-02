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


# NOTE: retained for historical migrations (e.g. users.0003) which import
# these helpers at load time. Live code uses apps.kaazbir.models instead.
def kyc_file_path(instance, filename: str) -> str:
    return f"kyc/{instance.user_id}/{instance.document_type}/{filename}"


def kyc_selfie_file_path(instance, filename: str) -> str:
    return f"kyc/{instance.kyc.user_id}/{instance.kyc.document_type}/selfies/{filename}"


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
