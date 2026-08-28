from django.contrib import admin

from .models import Earning, Mission, MissionApplication, MissionPicture, Review


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("title", "hirer", "kaazbir", "status", "origin", "created_at")
    list_filter = ("status", "origin", "payment_status")
    search_fields = ("title", "hirer__username", "kaazbir__username")


@admin.register(MissionApplication)
class MissionApplicationAdmin(admin.ModelAdmin):
    list_display = ("mission", "kaazbir", "action", "budget", "created_at")
    list_filter = ("action",)
    search_fields = ("mission__title", "kaazbir__username")


@admin.register(MissionPicture)
class MissionPictureAdmin(admin.ModelAdmin):
    list_display = ("mission", "image")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("mission", "hirer", "kaazbir", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("hirer__username", "kaazbir__username")


@admin.register(Earning)
class EarningAdmin(admin.ModelAdmin):
    list_display = ("kaazbir", "mission", "amount", "created_at")
    list_filter = ("kaazbir",)
    search_fields = ("kaazbir__username", "mission__title")
