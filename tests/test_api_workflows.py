"""
KaazDaak API Integration Tests
Tests all API workflows against the live server at http://74.225.251.88
Run: pytest tests/test_api_workflows.py -v --tb=short --no-header -p no:django
"""

import io
import uuid

import pytest
import requests

BASE_URL = "http://74.225.251.88"


def api(method, path, session=None, json=None, data=None, files=None, params=None):
    """Helper to make API calls and return (status_code, response_json).

    When files is provided, `json` fields should be passed via `data` as strings
    (requests can't mix json= and files=).
    """
    url = f"{BASE_URL}{path}"
    headers = {}
    if session:
        headers["Authorization"] = f"Bearer {session['token']}"
    kwargs = {"params": params, "headers": headers, "timeout": 30}
    if files:
        kwargs["files"] = files
        if data:
            kwargs["data"] = data
    else:
        if json is not None:
            kwargs["json"] = json
        if data is not None:
            kwargs["data"] = data
    resp = requests.request(method, url, **kwargs)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, resp.text


def success(body):
    """Assert response body indicates success."""
    assert body.get("success") is True, f"Expected success, got: {body}"


def error(body):
    """Assert response body indicates failure."""
    assert body.get("success") is False, f"Expected failure, got: {body}"


def paginate(body):
    """Assert response is paginated and return results list."""
    assert "count" in body["data"], f"Expected paginated response, got: {body['data']}"
    return body["data"]["results"]


def make_image_bytes(name="test.png"):
    """Create a minimal valid PNG in memory."""
    # 1x1 red pixel PNG
    import struct
    import zlib

    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\x00\x00"
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


# ============================================================================
# SECTION 12: System
# ============================================================================
class TestHealth:
    def test_health_check(self):
        status, body = api("GET", "/api/health/")
        assert status == 200
        assert body.get("status") == "healthy"


# ============================================================================
# SECTION 1-2: Auth Flow (uses conftest fixtures)
# ============================================================================
class TestLoginFlow:
    def test_hirer_login(self, hirer_session):
        assert hirer_session["token"] is not None
        assert hirer_session["user"]["role"] == "hirer"
        assert hirer_session["user"]["email"] == "sam@example.com"

    def test_kaazbir_login(self, kaazbir_session):
        assert kaazbir_session["token"] is not None
        assert kaazbir_session["user"]["role"] == "kaazbir"
        assert kaazbir_session["user"]["email"] == "shamiulhasan423@gmail.com"

    def test_login_invalid_credentials(self, base_url):
        status, body = api(
            "POST",
            "/api/v1/auth/login/",
            json={"identifier": "nonexistent@test.com", "password": "wrong"},
        )
        assert status == 401
        error(body)

    def test_hirer_me(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/auth/me/", session=hirer_session)
        assert status == 200
        success(body)
        assert body["data"]["role"] == "hirer"
        assert "id" in body["data"]

    def test_kaazbir_me(self, kaazbir_session, base_url):
        status, body = api("GET", "/api/v1/auth/me/", session=kaazbir_session)
        assert status == 200
        success(body)
        assert body["data"]["role"] == "kaazbir"
        assert "kaazbir_profile" in body["data"]

    def test_token_refresh(self, hirer_session, base_url):
        status, body = api(
            "POST",
            "/api/v1/auth/token/refresh/",
            json={"refresh": hirer_session["refresh"]},
        )
        assert status == 200
        success(body)
        assert "access" in body["data"]

    def test_unauthenticated_me(self, base_url):
        status, body = api("GET", "/api/v1/auth/me/")
        assert status == 401

    def test_hirer_logout(self, hirer_session, base_url):
        status, body = api(
            "POST",
            "/api/v1/auth/logout/",
            session=hirer_session,
            json={"refresh": hirer_session["refresh"]},
        )
        assert status == 200
        success(body)


# ============================================================================
# SECTION 3: KaazBir Profile
# ============================================================================
class TestKaazbirProfile:
    def test_get_profile(self, kaazbir_session, base_url):
        status, body = api("GET", "/api/v1/kaazbir/profile/", session=kaazbir_session)
        assert status == 200
        success(body)
        assert "id" in body["data"]
        assert "is_profile_complete" in body["data"]

    def test_update_profile(self, kaazbir_session, base_url):
        status, body = api(
            "POST",
            "/api/v1/kaazbir/profile/",
            session=kaazbir_session,
            json={
                "business_name": "Test Works",
                "division": "Dhaka",
                "district": "Dhaka",
                "upazila": "Mirpur",
                "location": "Mirpur 10, Dhaka",
                "service_start_time": "09:00:00",
                "service_end_time": "18:00:00",
            },
        )
        assert status == 200
        success(body)

    def test_hirer_cannot_access_kaazbir_profile(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/kaazbir/profile/", session=hirer_session)
        assert status == 403


# ============================================================================
# SECTION 4: KYC Verification
# ============================================================================
class TestKYC:
    @pytest.mark.xfail(
        reason="KYC requires valid image uploads; may fail with test data"
    )
    def test_submit_kyc(self, kaazbir_session, base_url):
        img = make_image_bytes()
        status, body = api(
            "POST",
            "/api/v1/auth/kyc/submit/",
            session=kaazbir_session,
            files={
                "front_image": ("front.png", io.BytesIO(img), "image/png"),
                "back_image": ("back.png", io.BytesIO(img), "image/png"),
            },
            data={
                "document_type": "national_id",
                "full_name": "Test User",
                "father_name": "Test Father",
                "date_of_birth": "1995-01-01",
                "address": "Mirpur 10, Dhaka",
                "post": "1230",
                "thana": "Mirpur",
                "district": "Dhaka",
                "division": "Dhaka",
                "consent": "true",
            },
        )
        assert status == 201
        success(body)
        assert body["data"]["document_type"] == "national_id"
        assert body["data"]["status"] == "pending"

    def test_hirer_cannot_submit_kyc(self, hirer_session, base_url):
        img = make_image_bytes()
        status, body = api(
            "POST",
            "/api/v1/auth/kyc/submit/",
            session=hirer_session,
            files={
                "front_image": ("front.png", io.BytesIO(img), "image/png"),
                "back_image": ("back.png", io.BytesIO(img), "image/png"),
            },
            data={
                "document_type": "national_id",
                "full_name": "Test",
                "father_name": "Father",
                "date_of_birth": "1995-01-01",
                "address": "Dhaka",
                "post": "1230",
                "thana": "Mirpur",
                "district": "Dhaka",
                "division": "Dhaka",
                "consent": "true",
            },
        )
        assert status == 403


# ============================================================================
# SECTIONS 4-6: Services & Catalog
# ============================================================================
class TestServices:
    def test_list_services(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/services/", session=hirer_session)
        assert status == 200
        success(body)
        results = paginate(body)
        assert len(results) > 0
        svc = results[0]
        assert "id" in svc
        assert "name" in svc
        assert "subservices" in svc

    def test_service_detail(self, hirer_session, base_url, service_id):
        status, body = api(
            "GET", f"/api/v1/services/{service_id}/", session=hirer_session
        )
        assert status == 200
        success(body)
        assert body["data"]["id"] == service_id
        assert "subservices" in body["data"]

    def test_service_not_found(self, hirer_session, base_url):
        fake_id = str(uuid.uuid4())
        status, body = api("GET", f"/api/v1/services/{fake_id}/", session=hirer_session)
        assert status == 404


class TestSubserviceCustomFields:
    def test_get_custom_fields(self, base_url, subservice_id):
        status, body = api("GET", f"/api/v1/subservices/{subservice_id}/custom-fields/")
        assert status == 200
        success(body)
        assert isinstance(body["data"], list)


class TestKaazbirServices:
    def test_get_mine(self, kaazbir_session, base_url):
        status, body = api(
            "GET", "/api/v1/kaazbir/services/mine/", session=kaazbir_session
        )
        assert status == 200
        success(body)
        assert "services" in body["data"]

    def test_update_services(
        self, kaazbir_session, base_url, service_id, subservice_id
    ):
        status, body = api(
            "POST",
            "/api/v1/kaazbir/services/",
            session=kaazbir_session,
            json={
                "services": [
                    {
                        "service_id": service_id,
                        "subservice_ids": [subservice_id],
                    }
                ]
            },
        )
        assert status == 200
        success(body)
        assert "services" in body["data"]
        assert len(body["data"]["services"]) > 0

    def test_hirer_cannot_update_kaazbir_services(self, hirer_session, base_url):
        status, body = api(
            "POST",
            "/api/v1/kaazbir/services/",
            session=hirer_session,
            json={"services": []},
        )
        assert status == 403


# ============================================================================
# SECTION 7: Campaigns & Offers
# ============================================================================
class TestCampaigns:
    def test_list_offers(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/offers/", session=hirer_session)
        assert status == 200
        success(body)
        assert "count" in body["data"]
        assert "results" in body["data"]


# ============================================================================
# SECTION 8: Missions (Creation, Feed, Detail)
# ============================================================================
class TestMissions:
    @pytest.fixture(scope="class")
    def created_mission(self, hirer_session, base_url, service_id, subservice_id):
        status, body = api(
            "POST",
            "/api/v1/missions/",
            session=hirer_session,
            data={
                "title": f"Test Mission {uuid.uuid4().hex[:8]}",
                "description": "Automated test mission - plumbing repair",
                "service_id": service_id,
                "subservice_id": subservice_id,
                "budget": "500.00",
                "location": "Mirpur 10, Dhaka",
                "delivery_location": "Gulshan, Dhaka",
                "custom_fields_data": "{}",
            },
        )
        assert status == 201, f"Mission creation failed: {body}"
        success(body)
        return body["data"]

    def test_create_mission(self, created_mission):
        assert "id" in created_mission
        assert created_mission["mission"]["status"] == "open"
        assert created_mission["mission"]["origin"] == "hirer_posted"

    def test_list_feed(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/missions/feed/", session=hirer_session)
        assert status == 200
        success(body)
        paginate(body)

    def test_list_feed_with_filter(self, hirer_session, base_url, service_id):
        status, body = api(
            "GET",
            "/api/v1/missions/feed/",
            session=hirer_session,
            params={"service_id": service_id},
        )
        assert status == 200
        success(body)

    def test_mission_detail(self, hirer_session, base_url, created_mission):
        mission_id = created_mission["id"]
        status, body = api(
            "GET", f"/api/v1/missions/{mission_id}/", session=hirer_session
        )
        assert status == 200
        success(body)
        assert body["data"]["id"] == mission_id

    def test_mission_not_found(self, hirer_session, base_url):
        fake_id = str(uuid.uuid4())
        status, body = api("GET", f"/api/v1/missions/{fake_id}/", session=hirer_session)
        assert status in (404, 500)

    def test_kaazbir_cannot_create_mission(
        self, kaazbir_session, base_url, service_id, subservice_id
    ):
        status, body = api(
            "POST",
            "/api/v1/missions/",
            session=kaazbir_session,
            data={
                "title": "Should fail",
                "service_id": service_id,
                "subservice_id": subservice_id,
            },
        )
        assert status == 403


# ============================================================================
# SECTION 9: Bidding & Confirmation
# ============================================================================
class TestBidding:
    @pytest.fixture(scope="class")
    def bid_mission(
        self, hirer_session, kaazbir_session, base_url, service_id, subservice_id
    ):
        status, body = api(
            "POST",
            "/api/v1/missions/",
            session=hirer_session,
            data={
                "title": f"Bid Test Mission {uuid.uuid4().hex[:8]}",
                "description": "Mission for bid testing",
                "service_id": service_id,
                "subservice_id": subservice_id,
                "budget": "800.00",
                "location": "Dhanmondi, Dhaka",
            },
        )
        assert status == 201, f"Mission creation failed: {body}"
        mission_id = body["data"]["id"]
        return mission_id

    @pytest.fixture(scope="class")
    def reject_mission(
        self, hirer_session, kaazbir_session, base_url, service_id, subservice_id
    ):
        status, body = api(
            "POST",
            "/api/v1/missions/",
            session=hirer_session,
            data={
                "title": f"Reject Test Mission {uuid.uuid4().hex[:8]}",
                "description": "Mission for reject testing",
                "service_id": service_id,
                "subservice_id": subservice_id,
                "budget": "600.00",
                "location": "Uttara, Dhaka",
            },
        )
        assert status == 201, f"Mission creation failed: {body}"
        return body["data"]["id"]

    @pytest.fixture(scope="class")
    def no_budget_mission(
        self, hirer_session, kaazbir_session, base_url, service_id, subservice_id
    ):
        status, body = api(
            "POST",
            "/api/v1/missions/",
            session=hirer_session,
            data={
                "title": f"No Budget Mission {uuid.uuid4().hex[:8]}",
                "description": "Mission for budget validation test",
                "service_id": service_id,
                "subservice_id": subservice_id,
                "budget": "400.00",
                "location": "Mohammadpur, Dhaka",
            },
        )
        assert status == 201, f"Mission creation failed: {body}"
        return body["data"]["id"]

    def test_bid_on_mission(self, kaazbir_session, base_url, bid_mission):
        status, body = api(
            "POST",
            f"/api/v1/missions/{bid_mission}/bid/",
            session=kaazbir_session,
            json={"action": "bid", "budget": "750.00"},
        )
        assert status == 200
        success(body)
        assert body["data"]["status"] == "interested"

    def test_confirm_kaazbir(
        self, hirer_session, kaazbir_session, base_url, bid_mission
    ):
        kaazbir_id = kaazbir_session["user"]["id"]
        status, body = api(
            "POST",
            f"/api/v1/missions/{bid_mission}/confirm/",
            session=hirer_session,
            json={"kaazbir_id": kaazbir_id},
        )
        assert status == 200
        success(body)
        assert body["data"]["status"] == "accepted"
        assert body["data"]["payment_status"] == "held"

    def test_reject_mission(self, kaazbir_session, base_url, reject_mission):
        status, body = api(
            "POST",
            f"/api/v1/missions/{reject_mission}/bid/",
            session=kaazbir_session,
            json={"action": "reject"},
        )
        assert status == 200
        success(body)

    def test_bid_without_budget_fails(
        self, kaazbir_session, base_url, no_budget_mission
    ):
        status, body = api(
            "POST",
            f"/api/v1/missions/{no_budget_mission}/bid/",
            session=kaazbir_session,
            json={"action": "bid"},
        )
        assert status in (400, 422)

    def test_hirer_cannot_bid(self, hirer_session, base_url, bid_mission):
        status, body = api(
            "POST",
            f"/api/v1/missions/{bid_mission}/bid/",
            session=hirer_session,
            json={"action": "bid", "budget": "750.00"},
        )
        assert status == 403


# ============================================================================
# SECTION 10: Direct Offers (Chat)
# ============================================================================
class TestDirectOffers:
    def test_send_direct_offer(self, hirer_session, kaazbir_session, base_url):
        kaazbir_id = kaazbir_session["user"]["id"]
        status, body = api(
            "POST",
            f"/api/v1/chat/{kaazbir_id}/offers/",
            session=hirer_session,
            json={
                "order_title": f"Direct Offer {uuid.uuid4().hex[:6]}",
                "description": "Need help moving furniture",
                "budget": 1200,
                "location": "Banani, Dhaka",
                "work_location": "Banani, Dhaka",
            },
        )
        assert status == 201
        success(body)
        assert body["data"]["status"] == "offer_sent"

    def test_kaazbir_cannot_send_offer(self, kaazbir_session, base_url, hirer_session):
        hirer_id = hirer_session["user"]["id"]
        status, body = api(
            "POST",
            f"/api/v1/chat/{hirer_id}/offers/",
            session=kaazbir_session,
            json={
                "order_title": "Should fail",
                "budget": 500,
            },
        )
        assert status == 403

    def test_offer_missing_title(self, hirer_session, kaazbir_session, base_url):
        kaazbir_id = kaazbir_session["user"]["id"]
        status, body = api(
            "POST",
            f"/api/v1/chat/{kaazbir_id}/offers/",
            session=hirer_session,
            json={"budget": 500},
        )
        assert status == 400
        assert (
            "order_title" in body.get("message", "").lower() or body.get("data") is None
        )


# ============================================================================
# SECTION 11: Hirer Activity & Tasks
# ============================================================================
class TestHirerActivity:
    def test_recent_tasks(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/hirer/tasks/recent/", session=hirer_session)
        assert status == 200
        success(body)
        assert isinstance(body["data"], list)

    def test_tasks_mine(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/tasks/mine/", session=hirer_session)
        assert status == 200
        success(body)
        assert isinstance(body["data"], list)

    def test_hirer_activity_all(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/hirer/activity/", session=hirer_session)
        assert status == 200
        success(body)
        assert isinstance(body["data"], list)

    def test_hirer_activity_filter_pending(self, hirer_session, base_url):
        status, body = api(
            "GET",
            "/api/v1/hirer/activity/",
            session=hirer_session,
            params={"status": "pending"},
        )
        assert status == 200
        success(body)

    def test_hirer_activity_filter_hired(self, hirer_session, base_url):
        status, body = api(
            "GET",
            "/api/v1/hirer/activity/",
            session=hirer_session,
            params={"status": "hired"},
        )
        assert status == 200
        success(body)

    def test_hirer_cannot_access_kaazbir_activity(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/kaazbir/activities/", session=hirer_session)
        assert status == 403


# ============================================================================
# SECTION 12: Kasbir Discovery & Search
# ============================================================================
class TestKasbirSearch:
    def test_list_kasbirs(self, hirer_session, base_url, service_id):
        status, body = api(
            "GET",
            "/api/v1/kasbir/",
            session=hirer_session,
            params={"service_id": service_id},
        )
        assert status == 200
        success(body)
        assert isinstance(body["data"], list)

    def test_list_kasbirs_without_service_id(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/kasbir/", session=hirer_session)
        assert status == 200
        success(body)

    def test_available_kasbirs(self, hirer_session, base_url, service_id):
        status, body = api(
            "GET",
            "/api/v1/kasbir/available/",
            session=hirer_session,
            params={"service_id": service_id, "location": "Dhaka"},
        )
        assert status == 200
        success(body)

    def test_search_kasbirs(self, hirer_session, base_url, service_id):
        status, body = api(
            "GET",
            "/api/v1/kasbir/search/",
            session=hirer_session,
            params={"service_id": service_id, "min_rating": 3, "max_rate": 5000},
        )
        assert status == 200
        success(body)

    def test_category_kasbirs(self, hirer_session, base_url, service_id):
        status, body = api(
            "GET",
            f"/api/v1/categories/{service_id}/kasbirs/",
            session=hirer_session,
        )
        assert status == 200
        success(body)
        assert isinstance(body["data"], list)

    def test_kaazbir_can_also_search(self, kaazbir_session, base_url, service_id):
        status, body = api(
            "GET",
            "/api/v1/kasbir/search/",
            session=kaazbir_session,
            params={"service_id": service_id},
        )
        assert status == 200


# ============================================================================
# SECTION 13: Kaazbir Activities
# ============================================================================
class TestKaazbirActivity:
    def test_activities_list(self, kaazbir_session, base_url):
        status, body = api(
            "GET", "/api/v1/kaazbir/activities/", session=kaazbir_session
        )
        assert status == 200
        success(body)
        assert isinstance(body["data"], list)

    def test_activities_filter_pending(self, kaazbir_session, base_url):
        status, body = api(
            "GET",
            "/api/v1/kaazbir/activities/",
            session=kaazbir_session,
            params={"status": "pending"},
        )
        assert status == 200
        success(body)

    def test_activities_filter_in_progress(self, kaazbir_session, base_url):
        status, body = api(
            "GET",
            "/api/v1/kaazbir/activities/",
            session=kaazbir_session,
            params={"status": "in_progress"},
        )
        assert status == 200
        success(body)

    def test_activity_detail_not_found(self, kaazbir_session, base_url):
        fake_id = str(uuid.uuid4())
        status, body = api(
            "GET", f"/api/v1/kaazbir/activities/{fake_id}/", session=kaazbir_session
        )
        assert status == 404

    def test_hirer_cannot_access_kaazbir_activities(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/kaazbir/activities/", session=hirer_session)
        assert status == 403


# ============================================================================
# SECTION 14: Earnings & Stats
# ============================================================================
class TestEarningsStats:
    def test_earnings_weekly(self, kaazbir_session, base_url):
        status, body = api(
            "GET",
            "/api/v1/kaazbir/earnings/",
            session=kaazbir_session,
            params={"range": "weekly"},
        )
        assert status == 200
        success(body)
        assert "data" in body["data"]
        assert body["data"]["range"] == "weekly"

    def test_earnings_monthly(self, kaazbir_session, base_url):
        status, body = api(
            "GET",
            "/api/v1/kaazbir/earnings/",
            session=kaazbir_session,
            params={"range": "monthly"},
        )
        assert status == 200
        success(body)

    def test_acceptance_ratio(self, kaazbir_session, base_url):
        status, body = api(
            "GET", "/api/v1/kaazbir/stats/acceptance-ratio/", session=kaazbir_session
        )
        assert status == 200
        success(body)
        assert "interested" in body["data"]
        assert "accepted" in body["data"]
        assert "declined" in body["data"]

    def test_hirer_cannot_access_earnings(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/kaazbir/earnings/", session=hirer_session)
        assert status == 403

    def test_hirer_cannot_access_stats(self, hirer_session, base_url):
        status, body = api(
            "GET", "/api/v1/kaazbir/stats/acceptance-ratio/", session=hirer_session
        )
        assert status == 403


# ============================================================================
# SECTION 15: Reviews
# ============================================================================
class TestReviews:
    def test_review_average(self, kaazbir_session, base_url):
        status, body = api(
            "GET", "/api/v1/kaazbir/reviews/average/", session=kaazbir_session
        )
        assert status == 200
        success(body)
        assert "average_rating" in body["data"]
        assert "total_reviews" in body["data"]

    def test_review_list(self, kaazbir_session, base_url):
        status, body = api("GET", "/api/v1/kaazbir/reviews/", session=kaazbir_session)
        assert status == 200
        success(body)
        assert isinstance(body["data"], list)

    def test_hirer_cannot_access_reviews(self, hirer_session, base_url):
        status, body = api("GET", "/api/v1/kaazbir/reviews/", session=hirer_session)
        assert status == 403


# ============================================================================
# SECTION 16: Hirer Profiles & Media
# ============================================================================
class TestHirerProfile:
    def test_update_basic_info(self, hirer_session, base_url):
        status, body = api(
            "POST",
            "/api/v1/hirer/profile/basic-info/",
            session=hirer_session,
            json={
                "full_name": "Sam Updated",
                "email": "sam@example.com",
                "phone_number": "01712345678",
            },
        )
        assert status == 200
        success(body)
        assert body["data"]["full_name"] == "Sam Updated"

    def test_upload_media(self, hirer_session, base_url):
        img = make_image_bytes()
        status, body = api(
            "POST",
            "/api/v1/hirer/profile/media/",
            session=hirer_session,
            files={
                "certificate_picture": ("cert.png", io.BytesIO(img), "image/png"),
                "license_picture": ("license.png", io.BytesIO(img), "image/png"),
            },
            data={
                "certificate_name": "Test Certificate",
                "license_name": "Test License",
            },
        )
        assert status == 200
        success(body)

    def test_upload_profile_picture(self, hirer_session, base_url):
        img = make_image_bytes()
        status, body = api(
            "POST",
            "/api/v1/hirer/profile/picture/",
            session=hirer_session,
            files={"picture": ("profile.png", io.BytesIO(img), "image/png")},
        )
        assert status == 200
        success(body)
        assert "picture" in body["data"]

    def test_update_notifications(self, hirer_session, base_url):
        status, body = api(
            "PATCH",
            "/api/v1/hirer/settings/notifications/",
            session=hirer_session,
            json={
                "push_notifications": True,
                "sms_notifications": False,
                "email_notifications": True,
                "task_updates": True,
                "promotions_and_offers": False,
            },
        )
        assert status == 200
        success(body)
        assert body["data"]["push_notifications"] is True
        assert body["data"]["email_notifications"] is True

    def test_change_password(self, hirer_session, base_url):
        status, body = api(
            "POST",
            "/api/v1/hirer/change-password/",
            session=hirer_session,
            json={
                "old_password": "Change password: Sam",
                "new_password": "Change password: Sam",
                "confirm_password": "Change password: Sam",
            },
        )
        assert status == 200
        success(body)

    def test_change_password_wrong_old(self, hirer_session, base_url):
        status, body = api(
            "POST",
            "/api/v1/hirer/change-password/",
            session=hirer_session,
            json={
                "old_password": "WrongPassword123!",
                "new_password": "Change password: Sam",
                "confirm_password": "Change password: Sam",
            },
        )
        assert status == 400

    def test_kaazbir_cannot_access_hirer_profile(self, kaazbir_session, base_url):
        status, body = api(
            "POST",
            "/api/v1/hirer/profile/basic-info/",
            session=kaazbir_session,
            json={"full_name": "Fail", "email": "fail@test.com"},
        )
        assert status == 403

    def test_kaazbir_cannot_change_hirer_password(self, kaazbir_session, base_url):
        status, body = api(
            "POST",
            "/api/v1/hirer/change-password/",
            session=kaazbir_session,
            json={
                "old_password": "x",
                "new_password": "y",
                "confirm_password": "y",
            },
        )
        assert status == 403


# ============================================================================
# SECTIONS 17-18: Missing Endpoints (expected failures)
# ============================================================================
class TestMissingEndpoints:
    @pytest.mark.xfail(
        reason="No create-review endpoint exists (Review model has no API)"
    )
    def test_create_review(self, hirer_session, kaazbir_session, base_url):
        mission_id = str(uuid.uuid4())
        kaazbir_id = kaazbir_session["user"]["id"]
        status, body = api(
            "POST",
            f"/api/v1/missions/{mission_id}/review/",
            session=hirer_session,
            json={
                "kaazbir_id": kaazbir_id,
                "rating": 5,
                "review_text": "Great work!",
            },
        )
        assert status == 201
        success(body)

    @pytest.mark.xfail(reason="No mission status transition to in_progress endpoint")
    def test_start_mission(self, kaazbir_session, base_url):
        mission_id = str(uuid.uuid4())
        status, body = api(
            "POST",
            f"/api/v1/missions/{mission_id}/start/",
            session=kaazbir_session,
        )
        assert status == 200
        success(body)
        assert body["data"]["status"] == "in_progress"

    @pytest.mark.xfail(reason="No mission status transition to completed endpoint")
    def test_complete_mission(self, kaazbir_session, base_url):
        mission_id = str(uuid.uuid4())
        status, body = api(
            "POST",
            f"/api/v1/missions/{mission_id}/complete/",
            session=kaazbir_session,
        )
        assert status == 200
        success(body)
        assert body["data"]["status"] == "completed"

    @pytest.mark.xfail(reason="No cancel-mission endpoint")
    def test_cancel_mission(self, hirer_session, base_url):
        mission_id = str(uuid.uuid4())
        status, body = api(
            "POST",
            f"/api/v1/missions/{mission_id}/cancel/",
            session=hirer_session,
        )
        assert status == 200
        success(body)
