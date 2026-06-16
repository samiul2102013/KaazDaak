import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def verified_general_user():
    user = User.objects.create_user(
        username="verifieduser",
        email="verified@example.com",
        password="testpass123",
        full_name="Verified User",
        role="general",
        is_email_verified=True,
    )
    return user


@pytest.fixture
def verified_provider_user():
    user = User.objects.create_user(
        username="verifiedprovider",
        email="provider@example.com",
        phone_number="+8801712345678",
        password="testpass123",
        full_name="Verified Provider",
        role="provider",
        is_email_verified=True,
    )
    return user


@pytest.fixture
def unverified_user():
    user = User.objects.create_user(
        username="unverifieduser",
        email="unverified@example.com",
        password="testpass123",
        full_name="Unverified User",
        role="general",
        is_email_verified=False,
    )
    return user


@pytest.mark.django_db
class TestLogin:
    LOGIN_URL = "/api/v1/auth/login/"

    def test_login_with_email_success(self, api_client, verified_general_user):
        response = api_client.post(
            self.LOGIN_URL,
            {
                "identifier": verified_general_user.email,
                "password": "testpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["message"] == "Login successful."
        assert "access" in response.data["data"]
        assert "refresh" in response.data["data"]
        assert response.data["data"]["user"]["email"] == verified_general_user.email
        assert response.data["data"]["user"]["role"] == "general"

    def test_login_with_phone_success(self, api_client, verified_provider_user):
        response = api_client.post(
            self.LOGIN_URL,
            {
                "identifier": "01712345678",
                "password": "testpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["user"]["phone_number"] == "+8801712345678"
        assert response.data["data"]["user"]["role"] == "provider"

    def test_login_wrong_password(self, api_client, verified_general_user):
        response = api_client.post(
            self.LOGIN_URL,
            {
                "identifier": verified_general_user.email,
                "password": "wrongpassword",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert not response.data["success"]
        assert "Invalid credentials" in str(response.data["error"])

    def test_login_nonexistent_email(self, api_client):
        response = api_client.post(
            self.LOGIN_URL,
            {
                "identifier": "ghost@example.com",
                "password": "anypass",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Must not reveal whether the email exists
        assert "Invalid credentials" in str(response.data["error"])

    def test_login_unverified_email_blocked(self, api_client, unverified_user):
        response = api_client.post(
            self.LOGIN_URL,
            {
                "identifier": unverified_user.email,
                "password": "testpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not response.data["success"]
        assert "Email not verified" in str(response.data["error"])

    def test_login_no_identifier_field(self, api_client):
        response = api_client.post(
            self.LOGIN_URL,
            {"password": "testpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_empty_password(self, api_client, verified_general_user):
        response = api_client.post(
            self.LOGIN_URL,
            {
                "identifier": verified_general_user.email,
                "password": "",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCurrentUser:
    ME_URL = "/api/v1/auth/me/"

    def test_get_current_user_authenticated(self, api_client, verified_general_user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(verified_general_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = api_client.get(self.ME_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["email"] == verified_general_user.email
        assert response.data["data"]["role"] == "general"
        assert "provider_profile" in response.data["data"]

    def test_get_current_user_unauthenticated(self, api_client):
        response = api_client.get(self.ME_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestLogout:
    LOGOUT_URL = "/api/v1/auth/logout/"

    def test_logout_success(self, api_client, verified_general_user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(verified_general_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = api_client.post(
            self.LOGOUT_URL, {"refresh": str(refresh)}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["message"] == "Logged out successfully."

    def test_logout_unauthenticated(self, api_client):
        response = api_client.post(self.LOGOUT_URL, {"refresh": "abc"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenRefresh:
    REFRESH_URL = "/api/v1/auth/token/refresh/"

    def test_token_refresh_success(self, api_client, verified_general_user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(verified_general_user)
        response = api_client.post(
            self.REFRESH_URL, {"refresh": str(refresh)}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "access" in response.data["data"]
