"""
**File:** ``errors.py``
**Region:** ``ds_provider_mock_py_lib/errors``

Mock backend exceptions and status-code helpers.

Example:
    >>> from ds_provider_mock_py_lib.errors import MockBackendError, resolve_status_code
    >>> from ds_resource_plugin_py_lib.common.resource.linked_service.errors import LinkedServiceException
    >>> resolve_status_code(None, default=503)
    503
    >>> err = MockBackendError("boom", code="DS_LINKED_SERVICE_CONNECTION_ERROR", status_code=502)
    >>> err.status_code
    502
    >>> isinstance(err, LinkedServiceException)
    True
"""

from __future__ import annotations

from typing import Any

from ds_resource_plugin_py_lib.common.resource.linked_service.errors import LinkedServiceException


class MockBackendError(LinkedServiceException):
    """
    Failure raised by ``MockBackend.request()``.

    This is a linked-service contract error (``LinkedServiceException``).
    Dataset ``read()`` must wrap it as ``ReadError`` so it does not leak
    to dataset callers.
    """

    def __init__(
        self,
        message: str = "Mock backend operation failed",
        code: str = "DS_LINKED_SERVICE_MOCK_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize a mock backend error.

        Args:
            message: Human-readable error message.
            code: Machine-readable error code.
            status_code: HTTP-style status code carried by the backend error.
            details: Optional debugging context.
        """
        super().__init__(message, code, status_code, details)


def resolve_status_code(status_code: int | None, default: int) -> int:
    """
    Return ``status_code`` when set, otherwise ``default``.

    Args:
        status_code: Optional HTTP-style status code from settings.
        default: Fallback used when ``status_code`` is ``None``.

    Returns:
        A concrete integer status code.
    """
    if status_code is None:
        return default
    return status_code
