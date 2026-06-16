import pytest
from django.db import IntegrityError

from apps.users.models import OTP, ProviderProfile, User


@pytest.mark.django_db
class TestUserModel:
    def test_create_user_with_email(self):
        user = User.objects.create_user(
            username="john",
            email="john@example.com",
            password="securepass123",
            full_name="John Doe",
        )
        assert user.username == "john"
        assert user.email == "john@example.com"
        assert user.check_password("securepass123")
        assert user.role == "general"
        assert not user.is_email_verified
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_user_with_phone(self):
        user = User.objects.create_user(
            username="jane",
            email="jane@example.com",
            phone_number="+8801712345678",
            password="securepass123",
            full_name="Jane Doe",
        )
        assert user.phone_number == "+8801712345678"

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            full_name="Admin",
        )
        assert admin.is_staff
        assert admin.is_superuser
        assert admin.role == "general"
        assert admin.is_email_verified

    def test_user_str(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass123",
            full_name="Test User",
        )
        assert str(user) == "testuser"

    def test_duplicate_email_raises_error(self):
        User.objects.create_user(
            username="user1",
            email="dup@example.com",
            password="pass123",
            full_name="User One",
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username="user2",
                email="dup@example.com",
                password="pass123",
                full_name="User Two",
            )

    def test_user_has_email_or_phone_constraint(self):
        with pytest.raises(IntegrityError):
            user = User(
                username="nophone_noemail",
                full_name="No Contact",
            )
            user.save()


@pytest.mark.django_db
class TestProviderProfileModel:
    def test_create_provider_profile(self):
        user = User.objects.create_user(
            username="provider1",
            email="provider@example.com",
            password="pass123",
            full_name="Provider One",
            role="provider",
        )
        profile = ProviderProfile.objects.create(
            user=user,
            business_name="Test Biz",
            service_category="Cleaning",
            address="123 Main St",
        )
        assert profile.business_name == "Test Biz"
        assert profile.service_category == "Cleaning"
        assert profile.address == "123 Main St"
        assert str(profile) == "Test Biz (provider1)"

    def test_provider_profile_one_to_one(self):
        user = User.objects.create_user(
            username="provider2",
            email="provider2@example.com",
            password="pass123",
            full_name="Provider Two",
            role="provider",
        )
        ProviderProfile.objects.create(
            user=user, business_name="Biz", service_category="Cat", address="Addr"
        )
        assert hasattr(user, "provider_profile")
        assert user.provider_profile.business_name == "Biz"


@pytest.mark.django_db
class TestOTPModel:
    def test_create_otp(self):
        user = User.objects.create_user(
            username="otpuser",
            email="otp@example.com",
            password="pass123",
            full_name="OTP User",
        )
        otp = OTP.objects.create(
            user=user,
            code_hash="hashed_code",
            purpose="email_verification",
            expires_at="2099-01-01T00:00:00Z",
        )
        assert otp.attempts == 0
        assert not otp.is_used
        assert otp.purpose == "email_verification"
        assert str(otp) == f"OTP for {user.username} (email_verification)"

    def test_otp_is_expired(self):
        from datetime import timedelta

        from django.utils import timezone

        user = User.objects.create_user(
            username="expired_user",
            email="expired@example.com",
            password="pass123",
            full_name="Expired",
        )
        otp = OTP.objects.create(
            user=user,
            code_hash="hash",
            purpose="email_verification",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        assert otp.is_expired()

    def test_otp_is_not_expired(self):
        from datetime import timedelta

        from django.utils import timezone

        user = User.objects.create_user(
            username="valid_user",
            email="valid@example.com",
            password="pass123",
            full_name="Valid",
        )
        otp = OTP.objects.create(
            user=user,
            code_hash="hash",
            purpose="email_verification",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        assert not otp.is_expired()
