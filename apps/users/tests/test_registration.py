import pytest
from django.core import mail
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import KaazbirProfile, User
from apps.users.validators import normalize_bd_phone


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestHirerRegistration:
    REGISTER_URL = "/api/v1/auth/register/hirer/"

    def test_register_hirer_success(self, api_client):
        data = {
            "full_name": "John Doe",
            "email": "john.doe@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert (
            response.data["message"]
            == "Registration successful. Please verify your email."
        )
        assert response.data["data"]["email"] == "john.doe@example.com"

        user = User.objects.get(email="john.doe@example.com")
        assert user.username == "john.doe"
        assert user.full_name == "John Doe"
        assert user.role == "hirer"
        assert not user.is_email_verified
        assert user.check_password("StrongPass123!")

    def test_register_hirer_otp_email_sent(self, api_client):
        data = {
            "full_name": "OTP Test",
            "email": "otp_test@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        api_client.post(self.REGISTER_URL, data, format="json")
        assert len(mail.outbox) == 1
        assert "OTP" in mail.outbox[0].subject
        assert mail.outbox[0].to == ["otp_test@example.com"]

    def test_register_duplicate_email(self, api_client):
        data = {
            "full_name": "First User",
            "email": "dup@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        api_client.post(self.REGISTER_URL, data, format="json")
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not response.data["success"]
        assert "email" in str(response.data["error"])

    def test_register_weak_password(self, api_client):
        data = {
            "full_name": "Weak Pass",
            "email": "weak@example.com",
            "password": "123",
            "confirm_password": "123",
        }
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_full_name(self, api_client):
        data = {
            "email": "missing@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_mismatch(self, api_client):
        data = {
            "full_name": "Mismatch",
            "email": "mismatch@example.com",
            "password": "StrongPass123!",
            "confirm_password": "DifferentPass456!",
        }
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "confirm_password" in str(response.data["error"])

    def test_username_collision_different_domains(self, api_client):
        data1 = {
            "full_name": "User One",
            "email": "sam@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        api_client.post(self.REGISTER_URL, data1, format="json")
        assert User.objects.filter(username="sam").exists()

        data2 = {
            "full_name": "User Two",
            "email": "sam@test.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        api_client.post(self.REGISTER_URL, data2, format="json")
        assert User.objects.filter(username="sam2").exists()

        data3 = {
            "full_name": "User Three",
            "email": "sam@other.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        api_client.post(self.REGISTER_URL, data3, format="json")
        assert User.objects.filter(username="sam3").exists()


@pytest.mark.django_db
class TestKaazbirRegistration:
    REGISTER_URL = "/api/v1/auth/register/kaazbir/"

    def test_register_kaazbir_success(self, api_client):
        data = {
            "full_name": "KaazBir One",
            "email": "kaazbir@example.com",
            "phone_number": "01712345678",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "business_name": "Clean Co.",
            "service_category": "Cleaning",
            "address": "456 Main St",
        }
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["email"] == "kaazbir@example.com"
        assert response.data["data"]["phone_number"] == normalize_bd_phone(
            "01712345678"
        )

        user = User.objects.get(email="kaazbir@example.com")
        assert user.role == "kaazbir"
        assert user.phone_number == normalize_bd_phone("01712345678")
        assert user.kaazbir_profile.business_name == "Clean Co."
        assert user.kaazbir_profile.service_category == "Cleaning"
        assert user.kaazbir_profile.address == "456 Main St"

    def test_register_kaazbir_phone_validation(self, api_client):
        data = {
            "full_name": "Bad Phone",
            "email": "badphone@example.com",
            "phone_number": "123456",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone_number" in str(response.data["error"])

    def test_register_kaazbir_without_phone(self, api_client):
        data = {
            "full_name": "No Phone",
            "email": "nophone@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone_number" in str(response.data["error"])

    def test_register_kaazbir_duplicate_phone(self, api_client):
        data1 = {
            "full_name": "KaazBir One",
            "email": "kaaz1@example.com",
            "phone_number": "01712345678",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        api_client.post(self.REGISTER_URL, data1, format="json")

        data2 = {
            "full_name": "KaazBir Two",
            "email": "kaaz2@example.com",
            "phone_number": "01712345678",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = api_client.post(self.REGISTER_URL, data2, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_kaazbir_optional_profile_fields(self, api_client):
        data = {
            "full_name": "Minimal KaazBir",
            "email": "minimal@example.com",
            "phone_number": "01812345678",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="minimal@example.com")
        assert KaazbirProfile.objects.filter(user=user).exists()

    def test_register_kaazbir_phone_normalization(self, api_client):
        data = {
            "full_name": "Phone Norm",
            "email": "norm@example.com",
            "phone_number": "01912345678",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        api_client.post(self.REGISTER_URL, data, format="json")
        user = User.objects.get(email="norm@example.com")
        assert user.phone_number == "+8801912345678"

    def test_register_kaazbir_password_mismatch(self, api_client):
        data = {
            "full_name": "Mismatch KaazBir",
            "email": "mismatch_k@example.com",
            "phone_number": "01712345678",
            "password": "StrongPass123!",
            "confirm_password": "DifferentPass456!",
        }
        response = api_client.post(self.REGISTER_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "confirm_password" in str(response.data["error"])
