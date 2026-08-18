from django.contrib import admin

from .models import Campaign, KasbirService, Service, Subservice


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Subservice)
class SubserviceAdmin(admin.ModelAdmin):
    list_display = ("name", "service")
    list_filter = ("service",)
    search_fields = ("name", "service__name")


@admin.register(KasbirService)
class KasbirServiceAdmin(admin.ModelAdmin):
    list_display = ("kaazbir", "service")
    list_filter = ("service",)
    search_fields = ("kaazbir__username", "service__name")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "coupon_code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "coupon_code")
