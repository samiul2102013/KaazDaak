"""Env-driven throttling utilities.

Rate limits (and throttling on/off) are managed from .env so ops can tune or
disable them without code changes:

- ``THROTTLE_ENABLED=False`` turns every ``EnvScopedRateThrottle`` into a
  no-op (useful while debugging or in smoke environments).
- ``THROTTLE_RATES`` overrides per-scope rates, e.g.
  ``THROTTLE_RATES=login=10/minute,otp_resend=3/hour`` (unlisted scopes keep
  their defaults; see ``config.settings.base``).

Usage in a view:

    class MyView(APIView):
        throttle_classes = [EnvScopedRateThrottle]
        throttle_scope = "login"
"""

from django.conf import settings
from rest_framework.throttling import ScopedRateThrottle


class EnvScopedRateThrottle(ScopedRateThrottle):
    """A ``ScopedRateThrottle`` that can be switched off globally via the
    ``THROTTLE_ENABLED`` setting."""

    def allow_request(self, request, view):
        if not getattr(settings, "THROTTLE_ENABLED", True):
            return True
        return super().allow_request(request, view)
