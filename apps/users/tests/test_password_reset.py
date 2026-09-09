from datetime import timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import OTP, User
from apps.users.services import AuthService


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def reset_user():
    return User.objects.create_user(
        username="resetuser",
        email="resetuser@example.com",
        password="OldPass123!",
        full_name="Reset User",
        role="hirer",
        is_email_verified=True,
    )


def _extract_code():
    body = mail.outbox[-1].body
    for word in body.split():
        if word.isdigit() and len(word) == 6:
            return word
    return None


@pytest.mark.django_db
class TestForgotPasswordEndpoint:
    URL = "/api/v1/auth/forgot-password/"

    def test_forgot_password_existing_user(self, api_client, reset_user):
        response = api_client.post(self.URL, {"email": reset_user.email}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert (
            response.data["message"] == "If an account exists with this email, "
            "a password reset code has been sent."
        )
        assert len(mail.outbox) == 1
        otp = OTP.objects.filter(user=reset_user, purpose="password_reset").first()
        assert otp is not None

    def test_forgot_password_nonexistent_email(self, api_client):
        response = api_client.post(
            self.URL, {"email": "ghost@example.com"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestResetPasswordEndpoint:
    URL = "/api/v1/auth/reset-password/"

    def _request_reset(self, api_client, email):
        return api_client.post(
            "/api/v1/auth/forgot-password/", {"email": email}, format="json"
        )

    def test_reset_password_success(self, api_client, reset_user):
        self._request_reset(api_client, reset_user.email)
        code = _extract_code()
        assert code is not None
        response = api_client.post(
            self.URL,
            {
                "email": reset_user.email,
                "otp_code": code,
                "new_password": "NewStrongPass123!",
                "confirm_password": "NewStrongPass123!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Password reset successfully."
        reset_user.refresh_from_db()
        assert reset_user.check_password("NewStrongPass123!") is True

    def test_reset_password_wrong_otp(self, api_client, reset_user):
        self._request_reset(api_client, reset_user.email)
        response = api_client.post(
            self.URL,
            {
                "email": reset_user.email,
                "otp_code": "000000",
                "new_password": "NewStrongPass123!",
                "confirm_password": "NewStrongPass123!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_reset_password_expired_otp(self, api_client, reset_user):
        self._request_reset(api_client, reset_user.email)
        code = _extract_code()
        otp = OTP.objects.filter(
            user=reset_user, purpose="password_reset", is_used=False
        ).first()
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save(update_fields=["expires_at"])
        response = api_client.post(
            self.URL,
            {
                "email": reset_user.email,
                "otp_code": code,
                "new_password": "NewStrongPass123!",
                "confirm_password": "NewStrongPass123!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_password_max_attempts(self, api_client, reset_user):
        self._request_reset(api_client, reset_user.email)
        otp = OTP.objects.filter(
            user=reset_user, purpose="password_reset", is_used=False
        ).first()
        otp.attempts = settings.OTP_MAX_ATTEMPTS
        otp.save(update_fields=["attempts"])
        response = api_client.post(
            self.URL,
            {
                "email": reset_user.email,
                "otp_code": "123456",
                "new_password": "NewStrongPass123!",
                "confirm_password": "NewStrongPass123!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_reset_password_mismatched_passwords(self, api_client, reset_user):
        self._request_reset(api_client, reset_user.email)
        code = _extract_code()
        response = api_client.post(
            self.URL,
            {
                "email": reset_user.email,
                "otp_code": code,
                "new_password": "NewStrongPass123!",
                "confirm_password": "DifferentPass123!",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestResetPasswordService:
    def test_request_reset_nonexistent_email_silent(self):
        # Should not raise, should send no email.
        AuthService.request_password_reset("nobody@example.com")
        assert len(mail.outbox) == 0

    def test_reset_password_returns_false_for_unknown_user(self):
        result = AuthService.reset_password(
            "nobody@example.com", "123456", "NewStrongPass123!"
        )
        assert result is False
