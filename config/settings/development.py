from .base import *  # noqa: F403, F405

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Enable django-debug-toolbar in development
INSTALLED_APPS = list(INSTALLED_APPS) + [  # noqa: F405
    "debug_toolbar",
]

MIDDLEWARE = list(MIDDLEWARE) + [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# Required for django-debug-toolbar to show up
INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
