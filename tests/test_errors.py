"""
**File:** ``test_errors.py``
**Region:** ``tests/test_errors``

Mock backend error helper tests.
"""

from __future__ import annotations

from ds_provider_mock_py_lib.errors import MockBackendError, resolve_status_code


def test_resolve_status_code_uses_default_for_none() -> None:
    """It falls back to the provided default when status_code is None."""
    assert resolve_status_code(None, default=503) == 503


def test_resolve_status_code_keeps_explicit_value() -> None:
    """It returns an explicit status code unchanged."""
    assert resolve_status_code(429, default=500) == 429


def test_mock_backend_error_stores_fields() -> None:
    """It stores message, status_code, and code."""
    error = MockBackendError("boom", status_code=502, code="dropped")
    assert str(error) == "boom"
    assert error.message == "boom"
    assert error.status_code == 502
    assert error.code == "dropped"
