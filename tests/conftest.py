import pytest
import requests

BASE_URL = "http://74.225.251.88"
HIRER_EMAIL = "sam@example.com"
HIRER_PASSWORD = "Change password: Sam"
KAAZBIR_EMAIL = "shamiulhasan423@gmail.com"
KAAZBIR_PASSWORD = "Enter a new password for the user shamiulhasan423."


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def hirer_session(base_url):
    s = requests.Session()
    resp = s.post(
        f"{base_url}/api/v1/auth/login/",
        json={"identifier": HIRER_EMAIL, "password": HIRER_PASSWORD},
    )
    assert resp.status_code == 200, f"Hirer login failed: {resp.text}"
    body = resp.json()
    assert body["success"] is True
    token = body["data"]["access"]
    refresh = body["data"]["refresh"]
    user = body["data"]["user"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    return {"session": s, "token": token, "refresh": refresh, "user": user}


@pytest.fixture(scope="session")
def kaazbir_session(base_url):
    s = requests.Session()
    resp = s.post(
        f"{base_url}/api/v1/auth/login/",
        json={"identifier": KAAZBIR_EMAIL, "password": KAAZBIR_PASSWORD},
    )
    assert resp.status_code == 200, f"Kaazbir login failed: {resp.text}"
    body = resp.json()
    assert body["success"] is True
    token = body["data"]["access"]
    refresh = body["data"]["refresh"]
    user = body["data"]["user"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    return {"session": s, "token": token, "refresh": refresh, "user": user}


@pytest.fixture(scope="session")
def service_id(hirer_session, base_url):
    resp = hirer_session["session"].get(f"{base_url}/api/v1/services/")
    assert resp.status_code == 200
    results = resp.json()["data"]["results"]
    assert len(results) > 0, "No services found in DB"
    return results[0]["id"]


@pytest.fixture(scope="session")
def subservice_id(hirer_session, base_url, service_id):
    resp = hirer_session["session"].get(f"{base_url}/api/v1/services/{service_id}/")
    assert resp.status_code == 200
    subservices = resp.json()["data"]["subservices"]
    assert len(subservices) > 0, "No subservices found"
    return subservices[0]["id"]
