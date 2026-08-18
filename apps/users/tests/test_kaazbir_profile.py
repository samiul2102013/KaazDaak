import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import KaazbirProfile, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def kaazbir_user():
    user = User.objects.create_user(
        username="profilekaazbir",
        email="profile.kaazbir@example.com",
        phone_number="+8801712345678",
        password="testpass123",
        full_name="Profile KaazBir",
        role="kaazbir",
        is_email_verified=True,
    )
    KaazbirProfile.objects.create(
        user=user,
        business_name="Tech Fix BD",
        service_category="Home & Personal Services",
        address="Dhanmondi, Dhaka",
    )
    return user


@pytest.fixture
def kaazbir_client(api_client, kaazbir_user):
    refresh = RefreshToken.for_user(kaazbir_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def hirer_user():
    return User.objects.create_user(
        username="profilehirer",
        email="profile.hirer@example.com",
        password="testpass123",
        full_name="Profile Hirer",
        role="hirer",
        is_email_verified=True,
    )


@pytest.fixture
def hirer_client(api_client, hirer_user):
    refresh = RefreshToken.for_user(hirer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.mark.django_db
class TestKaazbirProfileModel:
    def test_new_fields_default_null(self, kaazbir_user):
        profile = kaazbir_user.kaazbir_profile
        assert profile.service_start_time is None
        assert profile.service_end_time is None
        assert profile.division is None
        assert profile.district is None
        assert profile.upazila is None
        assert profile.location is None
        assert profile.is_profile_complete is False


@pytest.mark.django_db
class TestKaazbirProfileGet:
    URL = "/api/v1/kaazbir/profile/"

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_hirer_forbidden(self, hirer_client):
        response = hirer_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_profile_success(self, kaazbir_client, kaazbir_user):
        response = kaazbir_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        data = response.data["data"]
        assert data["business_name"] == "Tech Fix BD"
        assert data["service_category"] == "Home & Personal Services"
        assert data["address"] == "Dhanmondi, Dhaka"
        assert data["kyc_verified"] is False
        assert data["is_profile_complete"] is False
        assert data["services"] == []


@pytest.mark.django_db
class TestKaazbirProfileUpdate:
    URL = "/api/v1/kaazbir/profile/"
    VALID_PAYLOAD = {
        "business_name": "Tech Fix BD",
        "service_start_time": "09:00:00",
        "service_end_time": "18:00:00",
        "division": "Dhaka",
        "district": "Dhaka",
        "upazila": "Dhanmondi",
        "location": "House 12, Road 5",
    }

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.URL, self.VALID_PAYLOAD, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_hirer_forbidden(self, hirer_client):
        response = hirer_client.post(self.URL, self.VALID_PAYLOAD, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_profile_success(self, kaazbir_client, kaazbir_user):
        response = kaazbir_client.post(self.URL, self.VALID_PAYLOAD, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["message"] == "Profile updated successfully."
        data = response.data["data"]
        assert data["id"] == str(kaazbir_user.kaazbir_profile.id)
        assert data["is_profile_complete"] is True

        kaazbir_user.kaazbir_profile.refresh_from_db()
        assert str(kaazbir_user.kaazbir_profile.service_start_time) == "09:00:00"
        assert str(kaazbir_user.kaazbir_profile.service_end_time) == "18:00:00"
        assert kaazbir_user.kaazbir_profile.division == "Dhaka"
        assert kaazbir_user.kaazbir_profile.district == "Dhaka"
        assert kaazbir_user.kaazbir_profile.upazila == "Dhanmondi"
        assert kaazbir_user.kaazbir_profile.location == "House 12, Road 5"
        assert kaazbir_user.kaazbir_profile.is_profile_complete is True

    def test_update_partial_keeps_incomplete(self, kaazbir_client, kaazbir_user):
        payload = {
            "business_name": "Tech Fix BD",
            "division": "Dhaka",
        }
        response = kaazbir_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["is_profile_complete"] is False

    def test_update_missing_business_name(self, kaazbir_client):
        payload = {
            "service_start_time": "09:00:00",
            "service_end_time": "18:00:00",
            "division": "Dhaka",
            "district": "Dhaka",
            "upazila": "Dhanmondi",
        }
        response = kaazbir_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False
        assert "business_name" in response.data["error"]

    def test_update_invalid_time(self, kaazbir_client):
        payload = dict(self.VALID_PAYLOAD)
        payload["service_start_time"] = "not-a-time"
        response = kaazbir_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestKaazbirProfileService:
    def test_is_complete_false_when_fields_missing(self, kaazbir_user):
        profile = kaazbir_user.kaazbir_profile
        from apps.users.services import KaazbirProfileService

        assert KaazbirProfileService.is_complete(profile) is False

    def test_get_or_create_returns_existing_profile(self, kaazbir_user):
        from apps.users.services import KaazbirProfileService

        profile = KaazbirProfileService.get_or_create_profile(kaazbir_user)
        assert profile == kaazbir_user.kaazbir_profile
