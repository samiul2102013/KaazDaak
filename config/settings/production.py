from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False

# Read ALLOWED_HOSTS from env (already defined in base.py, but redefined here for clarity)
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="",
    cast=lambda v: [s.strip() for s in v.split(",")] if v else [],
)

# Security Settings
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CONN_MAX_AGE = 60

# Sentry integration (optional — only activates if SENTRY_DSN is set)
SENTRY_DSN = config("SENTRY_DSN", default=None)
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
    )
