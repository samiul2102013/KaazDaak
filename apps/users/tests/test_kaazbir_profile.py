import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.kaazbir.models import KaazbirProfile
from apps.users.models import User


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
class TestKaazbirProfileCoordinates:
    URL = "/api/v1/kaazbir/profile/"

    def test_update_with_coordinates_success(self, kaazbir_client, kaazbir_user):
        payload = dict(TestKaazbirProfileUpdate.VALID_PAYLOAD)
        payload.update({"latitude": "24.747100", "longitude": "90.420300"})
        response = kaazbir_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        kaazbir_user.kaazbir_profile.refresh_from_db()
        assert str(kaazbir_user.kaazbir_profile.latitude) == "24.747100"
        assert str(kaazbir_user.kaazbir_profile.longitude) == "90.420300"

    def test_get_echoes_coordinates(self, kaazbir_client, kaazbir_user):
        payload = dict(TestKaazbirProfileUpdate.VALID_PAYLOAD)
        payload.update({"latitude": "24.747100", "longitude": "90.420300"})
        kaazbir_client.post(self.URL, payload, format="json")
        data = kaazbir_client.get(self.URL).data["data"]
        assert data["latitude"] == "24.747100"
        assert data["longitude"] == "90.420300"

    def test_update_without_coordinates_still_works(self, kaazbir_client, kaazbir_user):
        response = kaazbir_client.post(
            self.URL, TestKaazbirProfileUpdate.VALID_PAYLOAD, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        kaazbir_user.kaazbir_profile.refresh_from_db()
        assert kaazbir_user.kaazbir_profile.latitude is None
        assert kaazbir_user.kaazbir_profile.longitude is None

    def test_update_rejects_out_of_range_coordinates(self, kaazbir_client):
        payload = dict(TestKaazbirProfileUpdate.VALID_PAYLOAD)
        payload.update({"latitude": "91.000000", "longitude": "190.000000"})
        response = kaazbir_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "latitude" in response.data["error"]
        assert "longitude" in response.data["error"]


@pytest.mark.django_db
class TestKaazbirProfileService:
    def test_is_complete_false_when_fields_missing(self, kaazbir_user):
        profile = kaazbir_user.kaazbir_profile
        from apps.kaazbir.services import KaazbirProfileService

        assert KaazbirProfileService.is_complete(profile) is False

    def test_get_or_create_returns_existing_profile(self, kaazbir_user):
        from apps.kaazbir.services import KaazbirProfileService

        profile = KaazbirProfileService.get_or_create_profile(kaazbir_user)
        assert profile == kaazbir_user.kaazbir_profile


@pytest.mark.django_db
class TestKaazbirProfileCompletion:
    URL = "/api/v1/kaazbir/profile-completion/"

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_hirer_forbidden(self, hirer_client):
        response = hirer_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_fresh_profile_reports_only_basic_info(self, kaazbir_client):
        response = kaazbir_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"] == {
            "basic_info": True,
            "available_service_time": False,
            "service_location": False,
            "kyc": False,
        }

    def test_sections_flip_as_fields_fill(
        self, kaazbir_client, kaazbir_user, api_client
    ):
        kaazbir_client.post(
            "/api/v1/kaazbir/profile/",
            {
                "business_name": "Tech Fix BD",
                "service_start_time": "09:00:00",
                "service_end_time": "18:00:00",
                "division": "Dhaka",
                "district": "Dhaka",
                "upazila": "Savar",
                "location": "Savar Bazar",
            },
            format="json",
        )
        response = kaazbir_client.get(self.URL)
        assert response.data["data"] == {
            "basic_info": True,
            "available_service_time": True,
            "service_location": True,
            "kyc": False,
        }

    def test_kyc_true_after_submit(self, kaazbir_client, kaazbir_user):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        def make_image(name):
            buffer = BytesIO()
            Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
            return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

        kaazbir_client.post(
            "/api/v1/auth/kyc/submit/",
            {
                "document_type": "national_id",
                "front_image": make_image("front.png"),
                "back_image": make_image("back.png"),
                "full_name": "Profile KaazBir",
                "father_name": "Father",
                "date_of_birth": "1990-01-01",
                "address": "Dhanmondi",
                "post": "1205",
                "thana": "Dhanmondi",
                "district": "Dhaka",
                "division": "Dhaka",
                "consent": True,
            },
            format="multipart",
        )
        response = kaazbir_client.get(self.URL)
        assert response.data["data"]["kyc"] is True
