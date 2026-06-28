from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTP, KaazbirProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "phone_number",
        "full_name",
        "role",
        "is_email_verified",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "is_email_verified", "is_active", "is_staff")
    search_fields = ("username", "email", "phone_number", "full_name")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "full_name",
                    "email",
                    "phone_number",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "is_email_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "phone_number",
                    "full_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(KaazbirProfile)
class KaazbirProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "business_name", "service_category")
    search_fields = ("business_name", "service_category", "user__username")


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "purpose",
        "attempts",
        "is_used",
        "expires_at",
        "created_at",
    )
    list_filter = ("purpose", "is_used")
    search_fields = ("user__username", "user__email")
