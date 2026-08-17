import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class Category(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    picture = models.ImageField(upload_to="categories/", blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SubCategory(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="sub_categories"
    )
    name = models.CharField(max_length=100)
    picture = models.ImageField(upload_to="sub_categories/", blank=True, null=True)

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
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="kasbir_services"
    )
    sub_categories = models.ManyToManyField(
        SubCategory, related_name="kasbir_services", blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["kaazbir", "category"], name="unique_kaazbir_category"
            )
        ]

    def __str__(self):
        return f"{self.kaazbir.username} - {self.category.name}"


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
