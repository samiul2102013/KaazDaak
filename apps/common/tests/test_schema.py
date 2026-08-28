import pytest
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.validation import validate_schema
from rest_framework.test import APIClient


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
    assert services["properties"]["data"]["type"] == "array"


def test_request_body_serializer_is_documented(schema):
    login = schema["paths"]["/api/v1/auth/login/"]["post"]
    request_schema = _resolve_component(
        schema, login["requestBody"]["content"]["application/json"]["schema"]
    )
    assert set(request_schema["properties"]) == {"identifier", "password"}


def test_schema_endpoints_respond(api_client):
    assert api_client.get("/api/schema/").status_code == 200
    assert api_client.get("/api/docs/").status_code == 200
    assert api_client.get("/api/docs/redoc/").status_code == 200
