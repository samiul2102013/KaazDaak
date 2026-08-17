from rest_framework import serializers

from .models import Campaign, Category, SubCategory


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ["id", "name", "picture"]


class CategorySerializer(serializers.ModelSerializer):
    sub_categories = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "picture", "sub_categories"]


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = ["id", "title", "subtitle", "coupon_code", "picture"]
