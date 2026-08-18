from rest_framework import serializers

from .models import Campaign, Service, Subservice


class SubserviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subservice
        fields = ["id", "name", "picture"]


class ServiceSerializer(serializers.ModelSerializer):
    subservices = SubserviceSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = ["id", "name", "picture", "subservices"]


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = ["id", "title", "subtitle", "coupon_code", "picture"]
