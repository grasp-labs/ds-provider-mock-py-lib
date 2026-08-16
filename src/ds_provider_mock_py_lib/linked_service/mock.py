"""
**File:** ``mock.py``
**Region:** ``ds_provider_mock_py_lib/linked_service/mock``

Mock linked service for e2e testing.

Every failure mode is driven by settings so tests can tune behaviour
without touching code. Follows ``LINKED_SERVICE_CONTRACT.md``.

Field classification:
    exposed  : id, name, description, version, settings.*
    internal : _connection, _connect_attempts

Example:
    >>> from uuid import uuid4
    >>> from ds_provider_mock_py_lib.linked_service import MockLinkedService, MockLinkedServiceSettings
    >>> linked_service = MockLinkedService(
    ...     id=uuid4(),
    ...     name="mock-connection",
    ...     version="1.0.0",
    ...     settings=MockLinkedServiceSettings(),
    ... )
    >>> linked_service.connect()
    >>> linked_service.connection.call_count
    0
    >>> linked_service.close()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ds_common_logger_py_lib import Logger
from ds_resource_plugin_py_lib.common.resource.linked_service import LinkedService, LinkedServiceSettings
from ds_resource_plugin_py_lib.common.resource.linked_service.errors import (
    AuthenticationError,
    AuthorizationError,
    ConnectionError,
)

from ..enums import ConnectBehaviour, ResourceType
from ..errors import MockBackendError, resolve_status_code
from ..models import MockError

logger = Logger.get_logger(__name__, package=True)


@dataclass(kw_only=True)
class MockLinkedServiceSettings(LinkedServiceSettings):
    """Settings required to connect to the in-memory mock backend."""

    connect_behaviour: ConnectBehaviour = ConnectBehaviour.OK
    """What ``connect()`` does after optional transient failures."""

    connect_delay_ms: int = 0
    """Artificial delay applied during ``connect()``."""

    connect_fail_first_n: int = 0
    """First N ``connect()`` calls raise ``ConnectionError``, then succeed."""

    connect_error: MockError = field(
        default_factory=lambda: MockError(
            message="mock: cannot reach backend",
            code="mock_connect_failure",
            status_code=503,
        )
    )
    """Error spec used when ``connect()`` is configured to fail."""

    test_connection_ok: bool = True
    """When ``False``, ``test_connection()`` returns a failed health check."""

    test_connection_message: str = ""
    """Reason returned when ``test_connection_ok`` is ``False``."""

    latency_ms: int = 0
    """Artificial delay applied to every ``connection.request()`` call."""

    fail_on_call: int | None = None
    """Raise a raw backend error on the Nth ``request()`` call. ``None`` disables."""

    request_error: MockError = field(
        default_factory=lambda: MockError(
            message="mock backend failure",
            code="mock_backend_error",
            status_code=500,
        )
    )
    """Error spec used when ``fail_on_call`` matches."""

    drop_after_calls: int | None = None
    """Every ``request()`` after N calls raises. ``None`` disables."""

    drop_error: MockError = field(
        default_factory=lambda: MockError(
            message="connection dropped",
            code="connection_dropped",
            status_code=502,
        )
    )
    """Error spec used when the connection is dropped after N calls."""


class MockBackend:
    """
    Object returned by ``.connection``. Stands in for a real SDK client.

    Tracks call counts so tests can assert round-trips, and applies
    linked-service level failure rules independent of any dataset.
    """

    def __init__(self, settings: MockLinkedServiceSettings) -> None:
        """
        Initialize the mock backend.

        Args:
            settings: Linked-service settings that control request failures.
        """
        self.settings = settings
        self.call_count = 0
        self.closed = False

    def request(self, page: int) -> None:
        """
        Simulate one round-trip for ``page``.

        Args:
            page: 1-based page number requested by the dataset.

        Raises:
            MockBackendError: When the connection is closed or a failure rule matches.
        """
        if self.closed:
            raise MockBackendError("connection is closed", status_code=499, code="connection_closed")

        self.call_count += 1
        settings = self.settings
        if settings.latency_ms:
            time.sleep(settings.latency_ms / 1000)

        if settings.fail_on_call is not None and self.call_count == settings.fail_on_call:
            error = settings.request_error
            raise MockBackendError(
                f"{error.message} (call #{self.call_count}, page {page})",
                status_code=resolve_status_code(error.status_code, 500),
                code=error.code,
            )

        if settings.drop_after_calls is not None and self.call_count > settings.drop_after_calls:
            error = settings.drop_error
            raise MockBackendError(
                f"{error.message} (after {settings.drop_after_calls} calls)",
                status_code=resolve_status_code(error.status_code, 502),
                code=error.code,
            )

    def close(self) -> None:
        """Mark the backend handle as closed."""
        self.closed = True


@dataclass(kw_only=True)
class MockLinkedService(LinkedService[MockLinkedServiceSettings]):
    """In-memory linked service with tunable connect, health, and request failures."""

    settings: MockLinkedServiceSettings
    _connection: MockBackend | None = field(default=None, init=False, repr=False, metadata={"serialize": False})
    _connect_attempts: int = field(default=0, init=False, repr=False, metadata={"serialize": False})

    @property
    def type(self) -> ResourceType:
        """
        Get the type of the linked service.

        Returns:
            ResourceType
        """
        return ResourceType.LINKED_SERVICE

    @property
    def connection(self) -> MockBackend:
        """
        Return the mock backend established by ``connect()``.

        Returns:
            MockBackend: The connected backend handle.

        Raises:
            ConnectionError: If ``connect()`` has not been called.
        """
        if self._connection is None:
            raise ConnectionError(
                message="MockLinkedService is not connected. Call connect() first.",
                details={"provider": self.type.value, "linked_service": self.name},
            )
        return self._connection

    def connect(self) -> None:
        """
        Establish a connection to the mock backend.

        Raises:
            ConnectionError: When connect is configured to fail or is still in the
                transient-failure window.
            AuthenticationError: When ``connect_behaviour`` is ``authentication_error``.
            AuthorizationError: When ``connect_behaviour`` is ``authorization_error``.
        """
        settings = self.settings
        self._connect_attempts += 1
        if settings.connect_delay_ms:
            time.sleep(settings.connect_delay_ms / 1000)

        details = {
            "provider": self.type.value,
            "linked_service": self.name,
            "attempt": self._connect_attempts,
        }
        connect_error = settings.connect_error
        status_code = resolve_status_code(connect_error.status_code, 503)

        if self._connect_attempts <= settings.connect_fail_first_n:
            raise ConnectionError(
                message=(f"mock transient connect failure {self._connect_attempts}/{settings.connect_fail_first_n}"),
                code=connect_error.code,
                status_code=status_code,
                details=details,
            )

        if settings.connect_behaviour == ConnectBehaviour.CONNECTION_ERROR:
            raise ConnectionError(
                message=connect_error.message,
                code=connect_error.code,
                status_code=status_code,
                details=details,
            )
        if settings.connect_behaviour == ConnectBehaviour.AUTHENTICATION_ERROR:
            raise AuthenticationError(
                message=connect_error.message,
                code=connect_error.code,
                status_code=resolve_status_code(connect_error.status_code, 401),
                details=details,
            )
        if settings.connect_behaviour == ConnectBehaviour.AUTHORIZATION_ERROR:
            raise AuthorizationError(
                message=connect_error.message,
                code=connect_error.code,
                status_code=resolve_status_code(connect_error.status_code, 403),
                details=details,
            )

        self._connection = MockBackend(settings)
        logger.debug("Mock linked service connected on attempt %s.", self._connect_attempts)

    def test_connection(self) -> tuple[bool, str]:
        """
        Verify mock backend health without raising on failure.

        Returns:
            tuple[bool, str]: ``(True, "")`` on success, otherwise ``(False, reason)``.
        """
        settings = self.settings
        if not settings.test_connection_ok:
            return False, settings.test_connection_message or "mock: health check failed"
        if self._connection is None:
            return False, "not connected"
        if self._connection.closed:
            return False, "connection is closed"
        return True, ""

    def close(self) -> None:
        """Release the mock backend handle. Safe to call repeatedly."""
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        logger.debug("Mock linked service closed.")
