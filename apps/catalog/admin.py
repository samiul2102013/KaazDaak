from django.contrib import admin

from .models import Campaign, Category, KasbirService, SubCategory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name", "category__name")


@admin.register(KasbirService)
class KasbirServiceAdmin(admin.ModelAdmin):
    list_display = ("kaazbir", "category")
    list_filter = ("category",)
    search_fields = ("kaazbir__username", "category__name")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "coupon_code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "coupon_code")
