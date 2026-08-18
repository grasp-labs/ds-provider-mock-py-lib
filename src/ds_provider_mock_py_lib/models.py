"""
**File:** ``models.py``
**Region:** ``ds_provider_mock_py_lib/models``

Shared serializable models used by mock linked-service and dataset settings.

Example:
    >>> from ds_provider_mock_py_lib.models import MockError
    >>> spec = MockError(message="mock: cannot reach backend", code="DS_LINKED_SERVICE_CONNECTION_ERROR", status_code=503)
    >>> spec.serialize()["code"]
    'DS_LINKED_SERVICE_CONNECTION_ERROR'
"""

from __future__ import annotations

from dataclasses import dataclass

from ds_common_serde_py_lib import Serializable


@dataclass(kw_only=True)
class MockError(Serializable):
    """User-configurable error spec injected by mock settings."""

    message: str = "mock error"
    """Human-readable error message."""

    code: str = "DS_RESOURCE_ERROR"
    """Machine-readable error code."""

    status_code: int | None = 500
    """HTTP-style status code. ``None`` falls back to the raised exception default."""
