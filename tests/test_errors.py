"""
**File:** ``test_errors.py``
**Region:** ``tests/test_errors``

Mock backend error helper tests.
"""

from __future__ import annotations

from ds_resource_plugin_py_lib.common.resource.linked_service.errors import LinkedServiceException

from ds_provider_mock_py_lib.errors import MockBackendError, resolve_status_code


def test_resolve_status_code_uses_default_for_none() -> None:
    """It falls back to the provided default when status_code is None."""
    assert resolve_status_code(None, default=503) == 503


def test_resolve_status_code_keeps_explicit_value() -> None:
    """It returns an explicit status code unchanged."""
    assert resolve_status_code(429, default=500) == 429


def test_mock_backend_error_stores_fields() -> None:
    """It stores message, status_code, and code on a linked-service exception."""
    error = MockBackendError("boom", code="DS_LINKED_SERVICE_CONNECTION_ERROR", status_code=502)
    assert str(error) == "boom"
    assert error.message == "boom"
    assert error.status_code == 502
    assert error.code == "DS_LINKED_SERVICE_CONNECTION_ERROR"
    assert isinstance(error, LinkedServiceException)
