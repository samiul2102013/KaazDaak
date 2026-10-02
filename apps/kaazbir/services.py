from .models import KaazbirProfile, KYCVerification


class KaazbirProfileService:
    @staticmethod
    def get_or_create_profile(user):
        profile, _ = KaazbirProfile.objects.get_or_create(
            user=user,
            defaults={
                "business_name": "",
                "service_category": "",
                "address": "",
            },
        )
        return profile

    @staticmethod
    def update_profile(user, validated_data):
        profile = KaazbirProfileService.get_or_create_profile(user)
        for field, value in validated_data.items():
            setattr(profile, field, value)
        profile.is_profile_complete = KaazbirProfileService.is_complete(profile)
        profile.save()
        return profile

    @staticmethod
    def is_complete(profile):
        return bool(
            profile.business_name
            and profile.division
            and profile.district
            and profile.upazila
            and profile.service_start_time
            and profile.service_end_time
        )

    @staticmethod
    def completion_checklist(user):
        try:
            profile = user.kaazbir_profile
        except KaazbirProfile.DoesNotExist:
            profile = None
        return {
            "basic_info": bool((user.full_name or "").strip() and user.phone_number),
            "available_service_time": bool(
                profile and profile.service_start_time and profile.service_end_time
            ),
            "service_location": bool(
                profile and profile.division and profile.district and profile.upazila
            ),
            "kyc": KYCVerification.objects.filter(user=user).exists(),
        }
