from rest_framework import serializers

from .models import (
    Campaign,
    CustomField,
    KasbirService,
    Service,
    Subservice,
    SubserviceCustomField,
)


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


class KasbirServiceSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    subservices = SubserviceSerializer(many=True, read_only=True)

    class Meta:
        model = KasbirService
        fields = ["id", "service", "subservices"]


class KasbirServiceEntrySerializer(serializers.Serializer):
    service_id = serializers.UUIDField()
    subservice_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=True
    )

    def validate(self, attrs):
        service = Service.objects.filter(pk=attrs["service_id"]).first()
        if service is None:
            raise serializers.ValidationError({"service_id": "Service does not exist."})
        subservice_ids = attrs["subservice_ids"]
        subservices = list(
            Subservice.objects.filter(service=service, pk__in=subservice_ids).distinct()
        )
        if len(subservices) != len(set(subservice_ids)):
            raise serializers.ValidationError(
                {
                    "subservice_ids": (
                        "One or more subservices are invalid or do not "
                        "belong to the selected service."
                    )
                }
            )
        attrs["service"] = service
        attrs["subservices"] = subservices
        return attrs


class KaazbirServiceUpdateSerializer(serializers.Serializer):
    services = serializers.ListField(
        child=KasbirServiceEntrySerializer(), allow_empty=True
    )


class CustomFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomField
        fields = ["id", "name", "field_type", "options", "placeholder", "is_required"]


class SubserviceCustomFieldSerializer(serializers.ModelSerializer):
    custom_field = CustomFieldSerializer(read_only=True)

    class Meta:
        model = SubserviceCustomField
        fields = ["id", "custom_field", "order", "is_required"]
