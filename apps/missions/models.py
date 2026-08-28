import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class Mission(TimestampedModel):
    class Origin(models.TextChoices):
        HIRER_POSTED = "hirer_posted", "Hirer Posted"
        HIRER_DIRECT = "hirer_direct", "Hirer Direct Offer"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INTERESTED = "interested", "Interested"
        OFFER_SENT = "offer_sent", "Offer Sent"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        HELD = "held", "Held"
        RELEASED = "released", "Released"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    service = models.ForeignKey(
        "catalog.Service", on_delete=models.PROTECT, null=True, blank=True
    )
    subservice = models.ForeignKey(
        "catalog.Subservice", on_delete=models.PROTECT, null=True, blank=True
    )
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    kasbir_bid_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    final_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    per_hour_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    pickup_location = models.CharField(max_length=255, blank=True)
    delivery_location = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    hirer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="missions_posted",
    )
    kaazbir = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="missions_assigned",
    )
    origin = models.CharField(max_length=20, choices=Origin.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    delivery_time = models.DateTimeField(null=True, blank=True)
    custom_fields_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class MissionPicture(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mission = models.ForeignKey(
        Mission, on_delete=models.CASCADE, related_name="pictures"
    )
    image = models.ImageField(upload_to="missions/")

    def __str__(self):
        return f"Picture for {self.mission.title}"


class MissionApplication(TimestampedModel):
    class Action(models.TextChoices):
        BID = "bid", "Bid"
        REJECT = "reject", "Reject"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mission = models.ForeignKey(
        Mission, on_delete=models.CASCADE, related_name="applications"
    )
    kaazbir = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mission_applications",
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["mission", "kaazbir"]

    def __str__(self):
        return f"{self.kaazbir.username} - {self.mission.title} ({self.action})"


class Review(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mission = models.ForeignKey(
        Mission, on_delete=models.CASCADE, related_name="reviews"
    )
    hirer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_given",
    )
    kaazbir = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_received",
    )
    rating = models.PositiveSmallIntegerField()
    review_text = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["mission", "hirer"]

    def __str__(self):
        return f"Review for {self.kaazbir.username} by {self.hirer.username}"


class Earning(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kaazbir = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="earnings",
    )
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.kaazbir.username} - {self.amount} ({self.mission.title})"
