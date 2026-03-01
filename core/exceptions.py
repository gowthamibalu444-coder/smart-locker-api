"""
Global exception handler for DRF.
Returns consistent JSON error responses and logs all errors.
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps")


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that:
    - Wraps all errors in a consistent JSON envelope
    - Logs 5xx errors with full context
    - Logs 4xx errors at WARNING level
    """
    # Call DRF's default handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Structured error envelope
        error_data = {
            "success": False,
            "status_code": response.status_code,
            "error": _extract_error_detail(response.data),
        }

        # Log client errors at WARNING, server errors at ERROR
        view = context.get("view")
        request = context.get("request")
        user_id = str(request.user.id) if request and request.user.is_authenticated else "anonymous"

        log_extra = {
            "user_id": user_id,
            "action": f"{request.method} {request.path}" if request else "unknown",
        }

        if response.status_code >= 500:
            logger.error(
                f"Server error: {exc}",
                exc_info=exc,
                extra=log_extra,
            )
        else:
            logger.warning(
                f"Client error {response.status_code}: {exc}",
                extra=log_extra,
            )

        response.data = error_data
    else:
        # Unhandled exception — return 500
        logger.error(
            f"Unhandled exception: {exc}",
            exc_info=exc,
        )
        response = Response(
            {
                "success": False,
                "status_code": 500,
                "error": "An unexpected error occurred.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _extract_error_detail(data):
    """Flatten DRF error data into a human-readable format."""
    if isinstance(data, list):
        return " ".join(str(item) for item in data)
    if isinstance(data, dict):
        parts = []
        for key, value in data.items():
            if key == "detail":
                parts.append(str(value))
            else:
                if isinstance(value, list):
                    parts.append(f"{key}: {' '.join(str(v) for v in value)}")
                else:
                    parts.append(f"{key}: {value}")
        return " | ".join(parts)
    return str(data)
