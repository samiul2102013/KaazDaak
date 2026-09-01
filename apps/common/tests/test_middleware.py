import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_login_without_trailing_slash_no_redirect():
    c = APIClient()
    r = c.post(
        "/api/v1/auth/login", {"identifier": "x", "password": "x"}, format="json"
    )
    assert r.status_code != 301, "Should not 301 redirect"
    assert "Location" not in r, "No Location header expected"
    assert r.status_code in (200, 400, 401, 403)


@pytest.mark.django_db
def test_login_with_trailing_slash_still_works():
    c = APIClient()
    r = c.post(
        "/api/v1/auth/login/", {"identifier": "x", "password": "x"}, format="json"
    )
    assert r.status_code != 301
