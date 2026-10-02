from .models import HirerProfile


class HirerProfileService:
    @staticmethod
    def get_or_create_profile(user):
        profile, _ = HirerProfile.objects.get_or_create(user=user)
        return profile

    @staticmethod
    def update_profile(user, validated_data):
        profile = HirerProfileService.get_or_create_profile(user)
        for field, value in validated_data.items():
            setattr(profile, field, value)
        profile.is_profile_complete = HirerProfileService.is_complete(profile)
        profile.save()
        return profile

    @staticmethod
    def is_complete(profile):
        return bool(
            profile.address
            and profile.division
            and profile.district
            and profile.upazila
        )
