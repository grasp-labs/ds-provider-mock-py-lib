"""
**File:** ``test_linked_service_connect.py``
**Region:** ``tests/linked_service/test_linked_service_connect``

MockLinkedService connection management tests.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from ds_resource_plugin_py_lib.common.resource.linked_service.errors import (
    AuthenticationError,
    AuthorizationError,
    ConnectionError,
)

from ds_provider_mock_py_lib.enums import ConnectBehaviour
from ds_provider_mock_py_lib.errors import MockBackendError
from ds_provider_mock_py_lib.linked_service import MockLinkedService, MockLinkedServiceSettings
from ds_provider_mock_py_lib.models import MockError
from tests.mocks import create_linked_service


def test_connect_creates_backend() -> None:
    """It creates a backend handle on connect()."""
    linked_service = create_linked_service()
    linked_service.connect()
    assert linked_service.connection.call_count == 0
    assert linked_service.connection.closed is False


def test_connect_is_idempotent_with_fresh_handle() -> None:
    """It re-establishes the backend handle on subsequent connect() calls."""
    linked_service = create_linked_service()
    linked_service.connect()
    first = linked_service.connection
    first.request(1)
    linked_service.connect()
    assert linked_service.connection is not first
    assert linked_service.connection.call_count == 0


def test_connect_fails_first_n_then_succeeds() -> None:
    """It raises ConnectionError for the first N attempts, then connects."""
    linked_service = create_linked_service(connect_fail_first_n=2)
    with pytest.raises(ConnectionError):
        linked_service.connect()
    with pytest.raises(ConnectionError):
        linked_service.connect()
    linked_service.connect()
    assert linked_service.connection.call_count == 0


def test_connect_behaviour_connection_error() -> None:
    """It raises ConnectionError when connect_behaviour is connection_error."""
    linked_service = create_linked_service(connect_behaviour=ConnectBehaviour.CONNECTION_ERROR)
    with pytest.raises(ConnectionError) as exc_info:
        linked_service.connect()
    assert exc_info.value.status_code == 503


def test_connect_behaviour_authentication_error() -> None:
    """It raises AuthenticationError when connect_behaviour is authentication_error."""
    linked_service = create_linked_service(
        connect_behaviour=ConnectBehaviour.AUTHENTICATION_ERROR,
        connect_error=MockError(message="bad token", code="invalid_credentials", status_code=401),
    )
    with pytest.raises(AuthenticationError) as exc_info:
        linked_service.connect()
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "invalid_credentials"


def test_connect_behaviour_authorization_error() -> None:
    """It raises AuthorizationError when connect_behaviour is authorization_error."""
    linked_service = create_linked_service(
        connect_behaviour=ConnectBehaviour.AUTHORIZATION_ERROR,
        connect_error=MockError(message="forbidden", code="forbidden", status_code=None),
    )
    with pytest.raises(AuthorizationError) as exc_info:
        linked_service.connect()
    assert exc_info.value.status_code == 403


@patch("ds_provider_mock_py_lib.linked_service.mock.time.sleep")
def test_connect_applies_delay(mock_sleep: object) -> None:
    """It sleeps when connect_delay_ms is set."""
    linked_service = create_linked_service(connect_delay_ms=25)
    linked_service.connect()
    mock_sleep.assert_called_once_with(0.025)  # type: ignore[attr-defined]


def test_request_fail_on_call_raises_backend_error() -> None:
    """It raises MockBackendError on the configured request call."""
    linked_service = create_linked_service(fail_on_call=2)
    linked_service.connect()
    linked_service.connection.request(1)
    with pytest.raises(MockBackendError) as exc_info:
        linked_service.connection.request(2)
    assert exc_info.value.status_code == 500
    assert "call #2" in str(exc_info.value)


def test_request_drop_after_calls() -> None:
    """It raises after the configured number of successful calls."""
    linked_service = create_linked_service(drop_after_calls=1)
    linked_service.connect()
    linked_service.connection.request(1)
    with pytest.raises(MockBackendError) as exc_info:
        linked_service.connection.request(2)
    assert exc_info.value.code == "DS_LINKED_SERVICE_CONNECTION_ERROR"


def test_request_on_closed_connection() -> None:
    """It raises when the backend handle is closed."""
    linked_service = create_linked_service()
    linked_service.connect()
    linked_service.connection.close()
    with pytest.raises(MockBackendError) as exc_info:
        linked_service.connection.request(1)
    assert exc_info.value.code == "DS_LINKED_SERVICE_CONNECTION_ERROR"


@patch("ds_provider_mock_py_lib.linked_service.mock.time.sleep")
def test_request_applies_latency(mock_sleep: object) -> None:
    """It sleeps on each request when latency_ms is set."""
    linked_service = create_linked_service(latency_ms=10)
    linked_service.connect()
    linked_service.connection.request(1)
    mock_sleep.assert_called_once_with(0.01)  # type: ignore[attr-defined]


def test_close_is_idempotent() -> None:
    """It is safe to close an already-closed linked service."""
    linked_service = MockLinkedService(
        id=uuid4(),
        name="test-linked-service",
        version="1.0.0",
        settings=MockLinkedServiceSettings(),
    )
    linked_service.close()
    linked_service.connect()
    linked_service.close()
    linked_service.close()
    with pytest.raises(ConnectionError):
        _ = linked_service.connection


def test_context_manager_closes() -> None:
    """It closes the backend when leaving a with-block."""
    linked_service = create_linked_service()
    with linked_service:
        linked_service.connect()
        assert linked_service.connection.closed is False
    with pytest.raises(ConnectionError):
        _ = linked_service.connection
