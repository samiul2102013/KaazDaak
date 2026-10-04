import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


EXPECTED_BODY = {"status": "healthy", "message": "KaazDaak API is online"}


@pytest.mark.django_db
class TestHealthCheck:
    def test_canonical_health_url(self, api_client):
        response = api_client.get("/api/health/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == EXPECTED_BODY

    def test_versioned_health_alias_matches_canonical(self, api_client):
        response = api_client.get("/api/v1/health/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == EXPECTED_BODY
