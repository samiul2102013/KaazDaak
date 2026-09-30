import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_bd_phone_number(value):
    if not re.match(settings.BD_PHONE_REGEX, value):
        raise ValidationError(
            _(
                "Invalid Bangladeshi phone number. Must be 11 digits starting with 01 "
                "followed by a digit between 3-9 (e.g. 01712345678)."
            ),
            code="invalid_phone",
        )


def normalize_bd_phone(value):
    cleaned = re.sub(r"[\s\-()]", "", (value or "").strip())
    if cleaned.startswith("+88"):
        return cleaned
    if cleaned.startswith("88") and len(cleaned) == 13:
        return f"+{cleaned}"
    return f"+88{cleaned}"


def canonical_bd_local(value):
    cleaned = re.sub(r"[\s\-()]", "", (value or "").strip())
    if cleaned.startswith("+880"):
        return "0" + cleaned[4:]
    if cleaned.startswith("880"):
        return "0" + cleaned[3:]
    return cleaned
