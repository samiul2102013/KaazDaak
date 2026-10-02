import os
import subprocess
import sys

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.users.models import User


@pytest.mark.django_db
class TestJWTSettings:
    def test_default_lifetimes_preserve_historical_behavior(self):
        assert settings.ACCESS_TOKEN_LIFETIME_MINUTES == 15
        assert settings.REFRESH_TOKEN_LIFETIME_DAYS == 7
        assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds() == 900
        assert settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].days == 7

    def test_issued_access_token_matches_configured_lifetime(self):
        User.objects.create_user(
            username="jwtlife",
            email="jwtlife@example.com",
            password="StrongPass123!",
            full_name="JWT Life",
            role="hirer",
            is_email_verified=True,
        )
        response = APIClient().post(
            "/api/v1/auth/login/",
            {"email": "jwtlife@example.com", "password": "StrongPass123!"},
            format="json",
        )
        assert response.status_code == 200
        from rest_framework_simplejwt.tokens import AccessToken

        payload = AccessToken(response.data["data"]["access"]).payload
        assert payload["exp"] - payload["iat"] == 15 * 60

    def test_lifetimes_are_env_driven(self):
        env = {
            **os.environ,
            "ACCESS_TOKEN_LIFETIME_MINUTES": "60",
            "REFRESH_TOKEN_LIFETIME_DAYS": "30",
            "DJANGO_SETTINGS_MODULE": "config.settings.testing",
        }
        code = (
            "import django; django.setup();"
            "from django.conf import settings;"
            "assert settings.ACCESS_TOKEN_LIFETIME_MINUTES == 60;"
            "assert settings.REFRESH_TOKEN_LIFETIME_DAYS == 30;"
            "assert settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds() == 3600;"  # noqa: E501
            "assert settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].days == 30;"
            "print('env wiring OK')"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        assert "env wiring OK" in result.stdout
