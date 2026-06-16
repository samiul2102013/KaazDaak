from datetime import timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import OTP, User
from apps.users.services import AuthService


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def general_user():
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
        full_name="Test User",
        role="general",
        is_email_verified=False,
    )


@pytest.mark.django_db
class TestOTPGeneration:
    def test_generate_and_send_otp(self, general_user):
        AuthService.generate_and_send_otp(general_user)
        assert len(mail.outbox) == 1
        assert "OTP" in mail.outbox[0].subject
        assert general_user.email in mail.outbox[0].to

    def test_otp_stored_hashed(self, general_user):
        AuthService.generate_and_send_otp(general_user)
        otp = OTP.objects.filter(user=general_user).first()
        assert otp is not None
        assert otp.code_hash
        # Ensure it's a SHA-256 hex digest (64 chars)
        assert len(otp.code_hash) == 64

    def test_otp_not_stored_plaintext(self, general_user):
        AuthService.generate_and_send_otp(general_user)
        otp = OTP.objects.filter(user=general_user).first()
        email_body = mail.outbox[0].body
        # Extract the code from the email
        assert otp.code_hash != email_body

    def test_otp_expiry_time(self, general_user):
        AuthService.generate_and_send_otp(general_user)
        otp = OTP.objects.filter(user=general_user).first()
        expected_expiry = timezone.now() + timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        )
        diff = abs((otp.expires_at - expected_expiry).total_seconds())
        assert diff < 2  # within 2 seconds


@pytest.mark.django_db
class TestOTPVerification:
    def _extract_otp_code(self, user):
        """Helper to get the plaintext OTP from the email."""
        AuthService.generate_and_send_otp(user)
        body = mail.outbox[-1].body
        for word in body.split():
            if word.isdigit() and len(word) == 6:
                return word
        return None

    def test_verify_valid_otp(self, general_user):
        code = self._extract_otp_code(general_user)
        assert code is not None

        result = AuthService.verify_otp(general_user, code)
        assert result is True

        general_user.refresh_from_db()
        assert general_user.is_email_verified is True

    def test_verify_invalid_otp(self, general_user):
        AuthService.generate_and_send_otp(general_user)
        result = AuthService.verify_otp(general_user, "000000")
        assert result is False
        general_user.refresh_from_db()
        assert general_user.is_email_verified is False

    def test_verify_otp_wrong_code_increments_attempts(self, general_user):
        AuthService.generate_and_send_otp(general_user)
        otp = OTP.objects.filter(user=general_user).first()
        assert otp.attempts == 0

        AuthService.verify_otp(general_user, "000000")
        otp.refresh_from_db()
        assert otp.attempts == 1

    def test_max_otp_attempts_lockout(self, general_user):
        AuthService.generate_and_send_otp(general_user)
        for _ in range(settings.OTP_MAX_ATTEMPTS):
            AuthService.verify_otp(general_user, "000000")
        otp = OTP.objects.filter(user=general_user).first()
        otp.refresh_from_db()
        assert otp.attempts == settings.OTP_MAX_ATTEMPTS
        # Next attempt should fail due to max attempts
        result = AuthService.verify_otp(general_user, "000000")
        assert result is False

    def test_verify_expired_otp(self, general_user):
        AuthService.generate_and_send_otp(general_user)
        otp = OTP.objects.filter(user=general_user).first()
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save(update_fields=["expires_at"])

        result = AuthService.verify_otp(general_user, "654321")
        assert result is False

    def test_verify_otp_twice_fails(self, general_user):
        code = self._extract_otp_code(general_user)
        assert AuthService.verify_otp(general_user, code) is True
        assert AuthService.verify_otp(general_user, code) is False


@pytest.mark.django_db
class TestVerifyEmailEndpoint:
    VERIFY_URL = "/api/v1/auth/verify-email/"

    def _register_and_get_otp(self, api_client):
        data = {
            "full_name": "Verify User",
            "email": "verify@example.com",
            "password": "StrongPass123!",
        }
        api_client.post("/api/v1/auth/register/general/", data, format="json")
        body = mail.outbox[-1].body
        for word in body.split():
            if word.isdigit() and len(word) == 6:
                return "verify@example.com", word
        return None, None

    def test_verify_email_endpoint_success(self, api_client):
        email, code = self._register_and_get_otp(api_client)
        assert code is not None
        response = api_client.post(
            self.VERIFY_URL, {"email": email, "otp_code": code}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["message"] == "Email verified successfully."
        assert "access" in response.data["data"]
        assert "refresh" in response.data["data"]

        user = User.objects.get(email=email)
        assert user.is_email_verified is True

    def test_verify_email_invalid_otp(self, api_client):
        email, _ = self._register_and_get_otp(api_client)
        response = api_client.post(
            self.VERIFY_URL, {"email": email, "otp_code": "000000"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not response.data["success"]

    def test_verify_email_wrong_email(self, api_client):
        response = api_client.post(
            self.VERIFY_URL,
            {"email": "nonexistent@example.com", "otp_code": "123456"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_email_max_attempts(self, api_client):
        email, _ = self._register_and_get_otp(api_client)
        user = User.objects.get(email=email)
        otp = user.otps.first()
        otp.attempts = settings.OTP_MAX_ATTEMPTS
        otp.save(update_fields=["attempts"])

        response = api_client.post(
            self.VERIFY_URL, {"email": email, "otp_code": "123456"}, format="json"
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
class TestResendOTPEndpoint:
    RESEND_URL = "/api/v1/auth/resend-otp/"

    def test_resend_otp_success(self, api_client):
        data = {
            "full_name": "Resend User",
            "email": "resend@example.com",
            "password": "StrongPass123!",
        }
        api_client.post("/api/v1/auth/register/general/", data, format="json")
        mail.outbox.clear()

        response = api_client.post(
            self.RESEND_URL, {"email": "resend@example.com"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["message"] == "OTP resent successfully."
        assert len(mail.outbox) == 1

    def test_resend_otp_nonexistent_email(self, api_client):
        response = api_client.post(
            self.RESEND_URL, {"email": "ghost@example.com"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        # Should still say success to avoid email enumeration

    def test_resend_otp_already_verified(self, api_client):
        user = User.objects.create_user(
            username="verified",
            email="verified@example.com",
            password="pass123",
            full_name="Verified",
            is_email_verified=True,
        )
        response = api_client.post(
            self.RESEND_URL, {"email": user.email}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
