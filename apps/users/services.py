import hashlib
import logging
import random
import re

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import OTP, ProviderProfile, User
from .validators import normalize_bd_phone

logger = logging.getLogger(__name__)


def _generate_username_from_email(email):
    local_part = email.split("@")[0]
    base = local_part
    candidate = base
    suffix = 2
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


def _hash_otp(code):
    return hashlib.sha256(code.encode()).hexdigest()


def _constant_time_compare(a, b):
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0


def _generate_otp_code():
    return f"{random.randint(0, 999999):06d}"


class AuthService:
    @staticmethod
    @transaction.atomic
    def register_general_user(validated_data):
        email = validated_data["email"]
        username = _generate_username_from_email(email)
        user = User.objects.create_user(
            username=username,
            email=email,
            full_name=validated_data["full_name"],
            password=validated_data["password"],
            role="general",
            is_active=True,
            is_email_verified=False,
        )
        AuthService.generate_and_send_otp(user)
        return user

    @staticmethod
    @transaction.atomic
    def register_provider(validated_data):
        email = validated_data["email"]
        phone_number = normalize_bd_phone(validated_data["phone_number"])
        username = _generate_username_from_email(email)
        user = User.objects.create_user(
            username=username,
            email=email,
            phone_number=phone_number,
            full_name=validated_data["full_name"],
            password=validated_data["password"],
            role="provider",
            is_active=True,
            is_email_verified=False,
        )
        ProviderProfile.objects.create(
            user=user,
            business_name=validated_data.get("business_name", ""),
            service_category=validated_data.get("service_category", ""),
            address=validated_data.get("address", ""),
        )
        AuthService.generate_and_send_otp(user)
        return user

    @staticmethod
    def generate_and_send_otp(user):
        code = _generate_otp_code()
        hashed = _hash_otp(code)
        expires_at = timezone.now() + timezone.timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        )
        OTP.objects.create(
            user=user,
            code_hash=hashed,
            purpose="email_verification",
            expires_at=expires_at,
        )
        try:
            send_mail(
                subject="Your OTP Code for Email Verification",
                message=(
                    f"Hello {user.full_name},\n\n"
                    f"Your OTP code for email verification is: {code}\n"
                    f"This code expires in {settings.OTP_EXPIRY_MINUTES} minutes.\n\n"
                    f"If you did not request this, please ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(
                "OTP sent to user %s (purpose=email_verification)",
                user.username,
            )
        except Exception as e:
            logger.error(
                "Failed to send OTP email to user %s: %s",
                user.username,
                str(e),
            )

    @staticmethod
    def verify_otp(user, code):
        otp_qs = OTP.objects.filter(
            user=user,
            purpose="email_verification",
            is_used=False,
        ).order_by("-created_at")
        otp = otp_qs.first()
        if otp is None:
            logger.warning("No active OTP found for user %s", user.username)
            return False
        if otp.is_expired():
            logger.warning("Expired OTP used for user %s", user.username)
            return False
        if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            logger.warning("Max OTP attempts reached for user %s", user.username)
            return False
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        stored_hash = otp.code_hash
        if not _constant_time_compare(stored_hash, _hash_otp(code)):
            logger.info(
                "Incorrect OTP attempt %d for user %s",
                otp.attempts,
                user.username,
            )
            return False
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        logger.info(
            "Email verified for user %s (OTP validated)",
            user.username,
        )
        return True

    @staticmethod
    def authenticate_by_identifier(identifier, password):
        phone_pattern = re.compile(settings.BD_PHONE_REGEX)
        user = None
        if phone_pattern.match(identifier):
            normalized = normalize_bd_phone(identifier)
            try:
                user = User.objects.get(phone_number=normalized)
            except User.DoesNotExist:
                return None
            if not user.check_password(password):
                return None
            return user
        else:
            user = authenticate(username=identifier, password=password)
            if user is not None:
                return user
            try:
                user_obj = User.objects.get(email__iexact=identifier)
            except User.DoesNotExist:
                return None
            if user_obj.check_password(password):
                return user_obj
            return None
