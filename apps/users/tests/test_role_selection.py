import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import HirerProfile, KaazbirProfile, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestHirerFlagSelection:
    REGISTER_URL = "/api/v1/auth/register/hirer/"

    def base_data(self, **overrides):
        data = {
            "is_hirer": True,
            "name": "Hirer Person",
            "email": "hirer_flag@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        data.update(overrides)
        return data

    def test_register_hirer_with_flag_and_name(self, api_client):
        response = api_client.post(self.REGISTER_URL, self.base_data(), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="hirer_flag@example.com")
        assert user.role == "hirer"
        assert user.roles == ["hirer"]
        assert user.full_name == "Hirer Person"
        assert HirerProfile.objects.filter(user=user).exists()

    def test_register_hirer_creates_hirer_profile(self, api_client):
        api_client.post(
            self.REGISTER_URL,
            self.base_data(email="hirer_prof@example.com"),
            format="json",
        )
        user = User.objects.get(email="hirer_prof@example.com")
        assert hasattr(user, "hirer_profile")
        assert user.hirer_profile.is_profile_complete is False

    def test_register_hirer_without_flag_still_works(self, api_client):
        data = self.base_data(email="noflag@example.com")
        data.pop("is_hirer")
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="noflag@example.com")
        assert HirerProfile.objects.filter(user=user).exists()

    def test_register_hirer_with_full_name_still_works(self, api_client):
        data = self.base_data(email="fullname@example.com")
        data.pop("name")
        data["full_name"] = "Full Name Person"
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.get(email="fullname@example.com").full_name == (
            "Full Name Person"
        )

    def test_register_hirer_flag_false_rejected(self, api_client):
        response = api_client.post(
            self.REGISTER_URL,
            self.base_data(email="flagfalse@example.com", is_hirer=False),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "is_hirer" in str(response.data["error"])

    def test_register_hirer_missing_name_rejected(self, api_client):
        data = self.base_data(email="noname@example.com")
        data.pop("name")
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestKaazbirFlagSelection:
    REGISTER_URL = "/api/v1/auth/register/kaazbir/"

    def base_data(self, **overrides):
        data = {
            "is_kaazbir": True,
            "name": "Kaazbir Person",
            "email": "kaazbir_flag@example.com",
            "phone_number": "01712345678",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        data.update(overrides)
        return data

    def test_register_kaazbir_with_flag_and_name(self, api_client):
        response = api_client.post(self.REGISTER_URL, self.base_data(), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="kaazbir_flag@example.com")
        assert user.role == "kaazbir"
        assert user.roles == ["kaazbir"]
        assert user.full_name == "Kaazbir Person"
        assert KaazbirProfile.objects.filter(user=user).exists()

    def test_register_kaazbir_without_flag_still_works(self, api_client):
        data = self.base_data(email="knoflag@example.com")
        data.pop("is_kaazbir")
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_register_kaazbir_flag_false_rejected(self, api_client):
        response = api_client.post(
            self.REGISTER_URL,
            self.base_data(email="kflagfalse@example.com", is_kaazbir=False),
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "is_kaazbir" in str(response.data["error"])

    def test_register_kaazbir_missing_name_rejected(self, api_client):
        data = self.base_data(email="knoname@example.com")
        data.pop("name")
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
