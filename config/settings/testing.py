from .base import *  # noqa: F401, F403, F405

DEBUG = True
ALLOWED_HOSTS = ["*"]

SECRET_KEY = "test-secret-key-not-for-production"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CELERY_TASK_ALWAYS_EAGER = True

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Do not let throttle state leak between tests; the throttle behavior itself
# is unit-tested in apps/common/tests/test_throttling.py with override_settings.
THROTTLE_ENABLED = True
