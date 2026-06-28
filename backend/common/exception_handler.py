"""Custom DRF exception handling.

Guarantees every error response carries a flat string ``detail`` so the frontend
can always show one short message, while keeping DRF's per-field error map in the
body for clients that want it.
"""

from __future__ import annotations

from rest_framework.views import exception_handler as drf_exception_handler


def _first_message(data) -> str | None:
    """Depth-first search for the first human-readable error string."""
    if isinstance(data, dict):
        for value in data.values():
            message = _first_message(value)
            if message:
                return message
    elif isinstance(data, (list, tuple)):
        for value in data:
            message = _first_message(value)
            if message:
                return message
    elif isinstance(data, str):
        return data
    return None


def detail_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(data, dict) and "detail" not in data:
        message = _first_message(data)
        if message is not None:
            data["detail"] = message
    return response
