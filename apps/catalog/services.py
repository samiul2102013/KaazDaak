from django.db import transaction

from .models import KasbirService


class KaazbirServiceService:
    @staticmethod
    @transaction.atomic
    def replace_services(user, entries):
        selected_service_ids = {entry["service"].pk for entry in entries}
        KasbirService.objects.filter(kaazbir=user).exclude(
            service_id__in=selected_service_ids
        ).delete()
        for entry in entries:
            kasbir_service, _ = KasbirService.objects.get_or_create(
                kaazbir=user, service=entry["service"]
            )
            kasbir_service.subservices.set(entry["subservices"])
