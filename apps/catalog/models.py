import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class Service(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    picture = models.ImageField(upload_to="services/", blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subservice(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="subservices"
    )
    name = models.CharField(max_length=100)
    picture = models.ImageField(upload_to="subservices/", blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class KasbirService(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kaazbir = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kasbir_services",
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="kasbir_services"
    )
    subservices = models.ManyToManyField(
        Subservice, related_name="kasbir_services", blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["kaazbir", "service"], name="unique_kaazbir_service"
            )
        ]

    def __str__(self):
        return f"{self.kaazbir.username} - {self.service.name}"


class Campaign(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    coupon_code = models.CharField(max_length=50, blank=True)
    picture = models.ImageField(upload_to="campaigns/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class CustomField(TimestampedModel):
    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        DROPDOWN = "dropdown", "Dropdown"
        RADIO = "radio", "Radio"
        BOOLEAN = "boolean", "Boolean"
        IMAGE = "image", "Image Upload"
        LOCATION = "location", "Location"
        PRICE = "price", "Price"
        DATE = "date", "Date"
        TIME = "time", "Time"
        MULTI_SELECT = "multi_select", "Multi Select"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FieldType.choices)
    options = models.JSONField(default=list, blank=True)
    placeholder = models.CharField(max_length=255, blank=True)
    is_required = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SubserviceCustomField(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subservice = models.ForeignKey(
        Subservice, on_delete=models.CASCADE, related_name="custom_field_configs"
    )
    custom_field = models.ForeignKey(
        CustomField, on_delete=models.CASCADE, related_name="subservice_configs"
    )
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ["subservice", "custom_field"]

    def __str__(self):
        return f"{self.subservice.name} - {self.custom_field.name}"
