from drf_spectacular.openapi import AutoSchema

from apps.common.api_spec import build_tag_list


class EnvelopeAutoSchema(AutoSchema):
    """Reads optional ``request_serializer``/``response_serializer`` class
    attributes from plain ``APIView`` classes so drf-spectacular can document
    every endpoint of the project.

    The following view attributes are honoured:

    - ``request_serializer`` - serializer class used for POST/PUT/PATCH bodies
    - ``response_serializer`` - serializer (class or instance) or a dict
      mapping status codes to serializers for the success response
    - ``response_many`` - boolean, wrap ``response_serializer`` in a list
    - ``schema_skip_auth`` - boolean, omit the bearer security requirement

    Attributes can additionally be suffixed with ``_<method>`` (e.g.
    ``request_serializer_post``) when a view exposes different bodies per HTTP
    method.
    """

    def _lookup(self, name):
        method = self.method.lower()
        method_attr = getattr(self.view, "{}_{}".format(name, method), None)
        if method_attr is not None:
            return method_attr
        return getattr(self.view, name, None)

    def get_request_serializer(self):
        serializer = self._lookup("request_serializer")
        if serializer is not None:
            return serializer
        return super().get_request_serializer()

    def get_response_serializers(self):
        serializer = self._lookup("response_serializer")
        if serializer is not None:
            if isinstance(serializer, dict):
                return serializer
            return self._maybe_many(serializer)
        return super().get_response_serializers()

    def _maybe_many(self, serializer):
        if isinstance(serializer, type) and self._lookup("response_many"):
            return serializer(many=True)
        return serializer

    def get_auth(self):
        if getattr(self.view, "schema_skip_auth", False):
            return []
        return super().get_auth()

    def get_tags(self):
        tags = self._lookup("tags")
        if tags is not None:
            return tags
        return super().get_tags()


def _success_envelope(schema):
    return {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [True]},
            "message": {"type": "string"},
            "data": schema,
        },
        "required": ["success", "message", "data"],
    }


def _error_envelope(schema):
    return {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [False]},
            "error": schema,
            "message": {"type": "string"},
            "status_code": {"type": "integer"},
        },
        "required": ["success", "error", "message", "status_code"],
    }


def _apply_envelope(responses):
    for code, response in responses.items():
        content = response.get("content") or {}
        json_content = content.get("application/json")
        if json_content is None:
            continue
        schema = json_content.get("schema")
        if schema is None:
            continue
        if code == "default" or str(code)[0] in ("4", "5"):
            json_content["schema"] = _error_envelope(schema)
        else:
            json_content["schema"] = _success_envelope(schema)


def wrap_envelope_responses(result, generator, request, public):
    """Wrap response schemas in the project's uniform envelope so generated
    docs match the wire format: ``{success, message, data}`` for 2xx and
    ``{success, error, message, status_code}`` for errors.
    """
    for path, operations in result.get("paths", {}).items():
        if not path.startswith("/api/"):
            continue
        for method, operation in operations.items():
            if not isinstance(operation, dict):
                continue
            if method.lower() == "get" and path == "/api/health/":
                operation.pop("security", None)
                continue
            _apply_envelope(operation.get("responses", {}))

    result["components"].setdefault("schemas", {})
    result["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "enum": [False]},
            "error": {"type": "object"},
            "message": {"type": "string"},
            "status_code": {"type": "integer"},
        },
        "required": ["success", "error", "message", "status_code"],
    }

    result["tags"] = build_tag_list()
    return result
