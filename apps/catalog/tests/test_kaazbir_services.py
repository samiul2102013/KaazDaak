import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.catalog.models import KasbirService, Service, Subservice
from apps.users.models import KaazbirProfile, User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def kaazbir_user():
    user = User.objects.create_user(
        username="serviceskaazbir",
        email="services.kaazbir@example.com",
        phone_number="+8801712345678",
        password="testpass123",
        full_name="Services KaazBir",
        role="kaazbir",
        is_email_verified=True,
    )
    KaazbirProfile.objects.create(
        user=user,
        business_name="Services Fix BD",
        service_category="Home & Personal Services",
        address="Gulshan, Dhaka",
    )
    return user


@pytest.fixture
def kaazbir_client(api_client, kaazbir_user):
    refresh = RefreshToken.for_user(kaazbir_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def hirer_client(api_client):
    user = User.objects.create_user(
        username="serviceshirer",
        email="services.hirer@example.com",
        password="testpass123",
        full_name="Services Hirer",
        role="hirer",
        is_email_verified=True,
    )
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def service_a():
    return Service.objects.create(name="Home & Personal Services")


@pytest.fixture
def service_b():
    return Service.objects.create(name="Tutorial")


@pytest.fixture
def sub_a(service_a):
    return Subservice.objects.create(service=service_a, name="House Cleaning")


@pytest.fixture
def sub_b(service_a):
    return Subservice.objects.create(service=service_a, name="Painting")


@pytest.fixture
def sub_other(service_b):
    return Subservice.objects.create(service=service_b, name="Academic Tutor")


@pytest.mark.django_db
class TestKaazbirServiceUpdate:
    URL = "/api/v1/kaazbir/services/"

    def test_unauthenticated_returns_401(self, api_client, service_a, sub_a):
        payload = {
            "services": [
                {"service_id": str(service_a.id), "subservice_ids": [str(sub_a.id)]}
            ]
        }
        response = api_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_hirer_forbidden(self, hirer_client, service_a, sub_a):
        payload = {
            "services": [
                {"service_id": str(service_a.id), "subservice_ids": [str(sub_a.id)]}
            ]
        }
        response = hirer_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_success(
        self,
        kaazbir_client,
        kaazbir_user,
        service_a,
        service_b,
        sub_a,
        sub_b,
        sub_other,
    ):
        payload = {
            "services": [
                {
                    "service_id": str(service_a.id),
                    "subservice_ids": [str(sub_a.id), str(sub_b.id)],
                },
                {
                    "service_id": str(service_b.id),
                    "subservice_ids": [str(sub_other.id)],
                },
            ]
        }
        response = kaazbir_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        data = response.data["data"]["services"]
        assert len(data) == 2
        service_names = {entry["service"]["name"] for entry in data}
        assert service_names == {"Home & Personal Services", "Tutorial"}
        home_entry = next(
            e for e in data if e["service"]["name"] == "Home & Personal Services"
        )
        assert {s["name"] for s in home_entry["subservices"]} == {
            "House Cleaning",
            "Painting",
        }
        assert kaazbir_user.kasbir_services.count() == 2

    def test_update_replaces_previous_services(
        self, kaazbir_client, kaazbir_user, service_a, service_b, sub_a, sub_other
    ):
        KasbirService.objects.create(
            kaazbir=kaazbir_user, service=service_a
        ).subservices.add(sub_a)
        assert kaazbir_user.kasbir_services.count() == 1

        payload = {
            "services": [
                {
                    "service_id": str(service_b.id),
                    "subservice_ids": [str(sub_other.id)],
                }
            ]
        }
        response = kaazbir_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        remaining = list(kaazbir_user.kasbir_services.select_related("service"))
        assert len(remaining) == 1
        assert remaining[0].service == service_b
        assert list(remaining[0].subservices.all()) == [sub_other]

    def test_update_empty_list_clears_services(
        self, kaazbir_client, kaazbir_user, service_a, sub_a
    ):
        KasbirService.objects.create(
            kaazbir=kaazbir_user, service=service_a
        ).subservices.add(sub_a)
        response = kaazbir_client.post(self.URL, {"services": []}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert kaazbir_user.kasbir_services.count() == 0
        assert response.data["data"]["services"] == []

    def test_update_invalid_service_id(self, kaazbir_client, sub_a):
        payload = {
            "services": [
                {
                    "service_id": "00000000-0000-0000-0000-000000000000",
                    "subservice_ids": [str(sub_a.id)],
                }
            ]
        }
        response = kaazbir_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_update_subservice_not_in_service(
        self, kaazbir_client, service_a, sub_other
    ):
        payload = {
            "services": [
                {
                    "service_id": str(service_a.id),
                    "subservice_ids": [str(sub_other.id)],
                }
            ]
        }
        response = kaazbir_client.post(self.URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_update_requires_services_field(self, kaazbir_client):
        response = kaazbir_client.post(self.URL, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestKaazbirServiceMine:
    URL = "/api/v1/kaazbir/services/mine/"

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_hirer_forbidden(self, hirer_client):
        response = hirer_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_mine_returns_empty(self, kaazbir_client):
        response = kaazbir_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["services"] == []

    def test_mine_returns_saved_services(
        self, kaazbir_client, kaazbir_user, service_a, sub_a, sub_b
    ):
        kasbir_service = KasbirService.objects.create(
            kaazbir=kaazbir_user, service=service_a
        )
        kasbir_service.subservices.add(sub_a, sub_b)
        response = kaazbir_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]["services"]
        assert len(data) == 1
        assert data[0]["service"]["name"] == "Home & Personal Services"
        assert {s["name"] for s in data[0]["subservices"]} == {
            "House Cleaning",
            "Painting",
        }
