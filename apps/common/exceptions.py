from rest_framework.views import exception_handler


def _extract_message(error_data):
    if isinstance(error_data, str):
        return error_data
    if isinstance(error_data, dict):
        detail = error_data.get("detail")
        if detail:
            return (
                detail
                if isinstance(detail, str)
                else str(detail[0] if isinstance(detail, list) else detail)
            )
        for value in error_data.values():
            if isinstance(value, list) and value:
                return str(value[0])
            return str(value)
    if isinstance(error_data, list) and error_data:
        return str(error_data[0])
    return "An error occurred"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        error_data = response.data
        response.data = {
            "success": False,
            "error": error_data,
            "message": _extract_message(error_data),
            "status_code": response.status_code,
        }
    return response
