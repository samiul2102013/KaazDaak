from django.contrib import admin

from .models import KaazbirProfile, KYCSelfie, KYCVerification


@admin.register(KaazbirProfile)
class KaazbirProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "business_name",
        "service_category",
        "kyc_verified",
        "is_profile_complete",
    )
    search_fields = ("business_name", "service_category", "user__username")


class KYCSelfieInline(admin.TabularInline):
    model = KYCSelfie
    extra = 0


@admin.register(KYCVerification)
class KYCVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "document_type", "status", "consent", "created_at")
    list_filter = ("document_type", "status")
    search_fields = ("user__username", "user__email")
    inlines = [KYCSelfieInline]
