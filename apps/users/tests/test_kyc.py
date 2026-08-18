from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import KaazbirProfile, KYCSelfie, KYCVerification, User


def _make_image(name):
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def kaazbir_user():
    user = User.objects.create_user(
        username="kyckaazbir",
        email="kyc.kaazbir@example.com",
        phone_number="+8801712345678",
        password="testpass123",
        full_name="KYC KaazBir",
        role="kaazbir",
        is_email_verified=True,
    )
    KaazbirProfile.objects.create(
        user=user,
        business_name="KYC Fix BD",
        service_category="Home & Personal Services",
        address="Mirpur, Dhaka",
    )
    return user


@pytest.fixture
def kaazbir_client(api_client, kaazbir_user):
    refresh = RefreshToken.for_user(kaazbir_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def hirer_user():
    return User.objects.create_user(
        username="kychirer",
        email="kyc.hirer@example.com",
        password="testpass123",
        full_name="KYC Hirer",
        role="hirer",
        is_email_verified=True,
    )


@pytest.fixture
def hirer_client(api_client, hirer_user):
    refresh = RefreshToken.for_user(hirer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


def _kyc_payload(**overrides):
    payload = {
        "document_type": "national_id",
        "front_image": _make_image("front.png"),
        "back_image": _make_image("back.png"),
        "full_name": "KYC KaazBir",
        "father_name": "Father Name",
        "date_of_birth": "1995-01-01",
        "address": "Mirpur 10",
        "post": "1216",
        "thana": "Pallabi",
        "district": "Dhaka",
        "division": "Dhaka",
        "consent": True,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestKYCSelfieModel:
    def test_create_selfie_with_order(self, kaazbir_user):
        kyc = KYCVerification.objects.create(
            user=kaazbir_user,
            document_type="national_id",
            front_image=_make_image("front.png"),
            back_image=_make_image("back.png"),
        )
        KYCSelfie.objects.create(kyc=kyc, image=_make_image("selfie0.png"), order=0)
        KYCSelfie.objects.create(kyc=kyc, image=_make_image("selfie1.png"), order=1)
        assert kyc.selfies.count() == 2
        assert list(kyc.selfies.values_list("order", flat=True)) == [0, 1]
        assert str(kyc.selfies.first()) == "Selfie 0 for kyckaazbir"


@pytest.mark.django_db
class TestKYCSubmit:
    URL = "/api/v1/auth/kyc/submit/"

    def test_submit_with_selfies_success(self, kaazbir_client, kaazbir_user):
        response = kaazbir_client.post(
            self.URL,
            _kyc_payload(selfies=[_make_image("s1.png"), _make_image("s2.png")]),
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["document_type"] == "national_id"
        assert response.data["data"]["status"] == "pending"
        kyc = KYCVerification.objects.get(user=kaazbir_user)
        assert kyc.selfies.count() == 2
        assert list(kyc.selfies.values_list("order", flat=True)) == [0, 1]
        assert kyc.extracted_data["full_name"] == "KYC KaazBir"
        kaazbir_user.kaazbir_profile.refresh_from_db()
        assert kaazbir_user.kaazbir_profile.kyc_verified is False

    def test_submit_without_selfies_success(self, kaazbir_client, kaazbir_user):
        response = kaazbir_client.post(self.URL, _kyc_payload(), format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        kyc = KYCVerification.objects.get(user=kaazbir_user)
        assert kyc.selfies.count() == 0

    def test_submit_rejects_invalid_image(self, kaazbir_client):
        bad_file = SimpleUploadedFile(
            "fake.png", b"not-an-image", content_type="image/png"
        )
        response = kaazbir_client.post(
            self.URL,
            _kyc_payload(front_image=bad_file),
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "front_image" in response.data["error"]

    def test_submit_without_consent(self, kaazbir_client):
        response = kaazbir_client.post(
            self.URL,
            _kyc_payload(consent=False),
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_hirer_forbidden(self, hirer_client):
        response = hirer_client.post(self.URL, _kyc_payload(), format="multipart")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.URL, _kyc_payload(), format="multipart")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
