"""
**File:** ``errors.py``
**Region:** ``ds_provider_mock_py_lib/errors``

Mock backend exceptions and status-code helpers.

Example:
    >>> from ds_provider_mock_py_lib.errors import MockBackendError, resolve_status_code
    >>> resolve_status_code(None, default=503)
    503
    >>> err = MockBackendError("boom", status_code=502, code="connection_dropped")
    >>> err.status_code
    502
"""

from __future__ import annotations


class MockBackendError(Exception):
    """
    Raw mock-backend exception.

    Datasets must wrap this as a contract error and never leak it to callers.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str = "mock_backend_error",
    ) -> None:
        """
        Initialize a mock backend error.

        Args:
            message: Human-readable error message.
            status_code: HTTP-style status code carried by the backend error.
            code: Machine-readable error code.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


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
