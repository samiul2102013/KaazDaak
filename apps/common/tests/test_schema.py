import pytest
from django.apps import apps
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.validation import validate_schema
from rest_framework.test import APIClient

from apps.common.api_spec import SECTION_TAGS, SECTIONS


@pytest.fixture
def schema():
    return SchemaGenerator(patterns=None).get_schema(request=None, public=True)


@pytest.fixture
def api_client():
    return APIClient()


def _response_schema(schema, path, method="get", code="200"):
    operation = schema["paths"][path][method]
    return operation["responses"][code]["content"]["application/json"]["schema"]


def _resolve_component(schema, node):
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[-1]
        return schema["components"]["schemas"][name]
    return node


def test_schema_is_valid_openapi(schema):
    validate_schema(schema)
    assert schema["openapi"].startswith("3.")


def test_schema_documents_docs_endpoints(schema):
    assert "/api/schema/" not in schema["paths"]
    assert "/api/docs/" not in schema["paths"]
    assert "/api/docs/redoc/" not in schema["paths"]


def test_success_responses_use_uniform_envelope(schema):
    login = _response_schema(schema, "/api/v1/auth/login/", method="post")
    assert set(login["properties"]) == {"success", "message", "data"}
    assert login["properties"]["success"]["enum"] == [True]
    assert "$ref" in login["properties"]["data"]


def test_login_does_not_require_auth_in_schema(schema):
    login = schema["paths"]["/api/v1/auth/login/"]["post"]
    assert "security" not in login


def test_register_uses_201(schema):
    register = schema["paths"]["/api/v1/auth/register/hirer/"]["post"]
    assert "201" in register["responses"]
    assert "200" not in register["responses"]


def test_authenticated_endpoints_require_bearer(schema):
    me = schema["paths"]["/api/v1/auth/me/"]["get"]
    assert me.get("security") == [{"jwtAuth": []}]
    assert "jwtAuth" in schema["components"]["securitySchemes"]


def test_health_is_not_enveloped(schema):
    health = _resolve_component(schema, _response_schema(schema, "/api/health/"))
    assert "success" not in health["properties"]


def test_list_endpoints_wrap_data_in_array(schema):
    services = _response_schema(schema, "/api/v1/services/", method="get")
    data = _resolve_component(schema, services["properties"]["data"])
    assert data["type"] == "object"
    assert data["properties"]["results"]["type"] == "array"


def test_request_body_serializer_is_documented(schema):
    login = schema["paths"]["/api/v1/auth/login/"]["post"]
    request_schema = _resolve_component(
        schema, login["requestBody"]["content"]["application/json"]["schema"]
    )
    assert set(request_schema["properties"]) == {"identifier", "email", "password"}


def test_schema_endpoints_respond(api_client):
    assert api_client.get("/api/schema/").status_code == 200
    assert api_client.get("/api/docs/").status_code == 200
    assert api_client.get("/api/docs/redoc/").status_code == 200


def test_operations_are_grouped_by_spec_section(schema):
    assert schema["paths"]["/api/v1/auth/login/"]["post"]["tags"] == [
        SECTION_TAGS["users-auth"]
    ]
    assert schema["paths"]["/api/v1/services/"]["get"]["tags"] == [
        SECTION_TAGS["services-subservices"]
    ]
    assert schema["paths"]["/api/v1/kasbir/search/"]["get"]["tags"] == [
        SECTION_TAGS["kaazbir-profiles"]
    ]
    assert schema["paths"]["/api/v1/auth/kyc/submit/"]["post"]["tags"] == [
        SECTION_TAGS["kyc-verification"]
    ]
    assert schema["paths"]["/api/v1/offers/"]["get"]["tags"] == [
        SECTION_TAGS["campaigns"]
    ]
    assert schema["paths"]["/api/v1/missions/feed/"]["get"]["tags"] == [
        SECTION_TAGS["missions-bids"]
    ]
    assert schema["paths"]["/api/v1/kaazbir/earnings/"]["get"]["tags"] == [
        SECTION_TAGS["earnings-stats"]
    ]
    assert schema["paths"]["/api/v1/hirer/profile/media/"]["post"]["tags"] == [
        SECTION_TAGS["hirer-profiles"]
    ]
    assert schema["paths"]["/api/health/"]["get"]["tags"] == [SECTION_TAGS["system"]]


def test_tag_metadata_is_declared_in_spec_order(schema):
    tag_names = [tag["name"] for tag in schema["tags"]]
    assert tag_names == [section.tag for section in SECTIONS.values()]
    assert all(tag["description"] for tag in schema["tags"])


def test_spec_sections_reference_real_model_tables():
    for section in SECTIONS.values():
        for model_path in section.models:
            app_label, model_name = model_path.split(".")
            model = apps.get_model(app_label, model_name)
            assert model._meta.db_table.startswith(f"{app_label}_")


def test_all_operation_tags_are_declared_in_spec(schema):
    valid_tags = {section.tag for section in SECTIONS.values()}
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if not isinstance(operation, dict) or "tags" not in operation:
                continue
            assert operation["tags"][0] in valid_tags, path
