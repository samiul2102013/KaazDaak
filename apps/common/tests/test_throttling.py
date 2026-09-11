import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from apps.common.throttling import EnvScopedRateThrottle


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


factory = APIRequestFactory()


def _request():
    """Mimic a DRF-dispatched request (throttling reads request.user)."""
    request = factory.get("/")
    request.user = AnonymousUser()
    return request


def _view(scope):
    class DummyView:
        pass

    view = DummyView()
    view.throttle_scope = scope
    return view


@override_settings(THROTTLE_ENABLED=False)
def test_disabled_throttle_never_blocks():
    throttle = EnvScopedRateThrottle()
    view = _view("login")
    for _ in range(15):
        assert throttle.allow_request(_request(), view) is True


def test_enabled_throttle_enforces_scope_rate():
    throttle = EnvScopedRateThrottle()
    throttle.THROTTLE_RATES = {"login": "2/minute"}
    view = _view("login")
    request = _request()
    results = [throttle.allow_request(request, view) for _ in range(3)]
    assert results == [True, True, False]


def test_enabled_throttle_skips_views_without_scope():
    throttle = EnvScopedRateThrottle()
    assert throttle.allow_request(_request(), object()) is True
