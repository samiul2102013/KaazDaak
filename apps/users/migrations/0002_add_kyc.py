import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.users.models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="kaazbirprofile",
            name="kyc_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="KYCVerification",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "document_type",
                    models.CharField(
                        choices=[
                            ("national_id", "National ID"),
                            ("passport", "Passport"),
                            ("driving_license", "Driving License"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "front_image",
                    models.ImageField(upload_to=apps.users.models.kyc_file_path),
                ),
                (
                    "back_image",
                    models.ImageField(upload_to=apps.users.models.kyc_file_path),
                ),
                (
                    "selfie_1",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=apps.users.models.kyc_file_path,
                    ),
                ),
                (
                    "selfie_2",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=apps.users.models.kyc_file_path,
                    ),
                ),
                (
                    "selfie_3",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=apps.users.models.kyc_file_path,
                    ),
                ),
                (
                    "selfie_4",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=apps.users.models.kyc_file_path,
                    ),
                ),
                ("extracted_data", models.JSONField(blank=True, default=dict)),
                ("consent", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("verified", "Verified"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kyc_verification",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
