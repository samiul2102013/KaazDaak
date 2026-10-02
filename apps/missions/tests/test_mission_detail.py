import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.missions.models import Mission
from apps.users.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def hirer_user():
    return User.objects.create_user(
        username="detailhirer",
        email="detail.hirer@example.com",
        password="testpass123",
        full_name="Detail Hirer",
        role="hirer",
        is_email_verified=True,
    )


@pytest.fixture
def hirer_client(api_client, hirer_user):
    refresh = RefreshToken.for_user(hirer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def mission(hirer_user):
    return Mission.objects.create(
        title="Fix my sink",
        hirer=hirer_user,
        origin=Mission.Origin.HIRER_POSTED,
    )


@pytest.mark.django_db
class TestMissionDetail:
    def url(self, pk):
        return f"/api/v1/missions/{pk}/"

    def test_unauthenticated_returns_401(self, api_client, mission):
        response = api_client.get(self.url(mission.pk))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_existing_mission_success(self, hirer_client, mission):
        response = hirer_client.get(self.url(mission.pk))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["id"] == str(mission.id)

    def test_unknown_uuid_returns_404_not_500(self, hirer_client):
        response = hirer_client.get(self.url(uuid.uuid4()))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["success"] is True
        assert response.data["data"] is None
