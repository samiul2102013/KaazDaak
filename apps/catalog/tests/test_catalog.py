import pytest
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.catalog.models import Campaign, KasbirService, Service, Subservice
from apps.users.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client):
    user = User.objects.create_user(
        username="cataloguser",
        email="catalog@example.com",
        password="testpass123",
        full_name="Catalog User",
        role="hirer",
        is_email_verified=True,
    )
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def service():
    return Service.objects.create(name="Home & Personal Services")


@pytest.fixture
def subservice(service):
    return Subservice.objects.create(service=service, name="House Cleaning")


@pytest.fixture
def campaign():
    return Campaign.objects.create(
        title="20% off first booking",
        subtitle="Valid for new users",
        coupon_code="WELCOME20",
        is_active=True,
    )


@pytest.mark.django_db
class TestServiceList:
    LIST_URL = "/api/v1/services/"

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_returns_services_with_subservices(
        self, authenticated_client, service, subservice
    ):
        response = authenticated_client.get(self.LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["message"] == "Services fetched successfully."
        data = response.data["data"]["results"]
        assert len(data) == 1
        assert data[0]["name"] == "Home & Personal Services"
        assert data[0]["subservices"][0]["name"] == "House Cleaning"


@pytest.mark.django_db
class TestServiceDetail:
    DETAIL_URL = "/api/v1/services/{pk}/"

    def test_detail_success(self, authenticated_client, service, subservice):
        url = self.DETAIL_URL.format(pk=service.id)
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["id"] == str(service.id)
        assert len(response.data["data"]["subservices"]) == 1

    def test_detail_not_found(self, authenticated_client):
        url = self.DETAIL_URL.format(pk="00000000-0000-0000-0000-000000000000")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["success"] is False


@pytest.mark.django_db
class TestCampaignList:
    LIST_URL = "/api/v1/campaigns/"

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_returns_only_active_campaigns(self, authenticated_client, campaign):
        Campaign.objects.create(
            title="Inactive offer",
            subtitle="Should not appear",
            coupon_code="OLD",
            is_active=False,
        )
        response = authenticated_client.get(self.LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        data = response.data["data"]["results"]
        assert len(data) == 1
        assert data[0]["title"] == "20% off first booking"
        assert data[0]["coupon_code"] == "WELCOME20"

    def test_list_empty_when_no_active_campaigns(self, authenticated_client):
        response = authenticated_client.get(self.LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["results"] == []


@pytest.mark.django_db
class TestKasbirServiceModel:
    def test_create_service(self, service, subservice):
        kaazbir = User.objects.create_user(
            username="kaazbircat",
            email="kaazbir.cat@example.com",
            password="testpass123",
            full_name="KaazBir Catalog",
            role="kaazbir",
            is_email_verified=True,
        )
        kasbir_service = KasbirService.objects.create(kaazbir=kaazbir, service=service)
        kasbir_service.subservices.add(subservice)
        assert kasbir_service.kaazbir == kaazbir
        assert kasbir_service.service == service
        assert list(kasbir_service.subservices.all()) == [subservice]
        assert str(kasbir_service) == "kaazbircat - Home & Personal Services"

    def test_duplicate_service_for_same_kaazbir_and_service(self, service):
        kaazbir = User.objects.create_user(
            username="kaazbirdup",
            email="kaazbir.dup@example.com",
            password="testpass123",
            full_name="KaazBir Duplicate",
            role="kaazbir",
            is_email_verified=True,
        )
        KasbirService.objects.create(kaazbir=kaazbir, service=service)
        with pytest.raises(IntegrityError):
            KasbirService.objects.create(kaazbir=kaazbir, service=service)
