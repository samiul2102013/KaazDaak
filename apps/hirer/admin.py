from django.contrib import admin

from .models import HirerMedia, HirerProfile


@admin.register(HirerProfile)
class HirerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "push_notifications", "created_at")
    search_fields = ("user__username",)


@admin.register(HirerMedia)
class HirerMediaAdmin(admin.ModelAdmin):
    list_display = ("user", "media_type", "name", "created_at")
    list_filter = ("media_type",)
    search_fields = ("user__username", "name")
