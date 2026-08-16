"""
**File:** ``test_linked_service_test_connection.py``
**Region:** ``tests/linked_service/test_linked_service_test_connection``

MockLinkedService test_connection() tests.
"""

from __future__ import annotations

from tests.mocks import create_linked_service


def test_test_connection_fails_when_not_connected() -> None:
    """It returns False when connect() has not been called."""
    linked_service = create_linked_service()
    success, message = linked_service.test_connection()
    assert success is False
    assert message == "not connected"


def test_test_connection_succeeds_when_connected() -> None:
    """It returns True after a successful connect()."""
    linked_service = create_linked_service()
    linked_service.connect()
    success, message = linked_service.test_connection()
    assert success is True
    assert message == ""


def test_test_connection_respects_settings_flag() -> None:
    """It returns the configured failure message without raising."""
    linked_service = create_linked_service(
        test_connection_ok=False,
        test_connection_message="backend unhealthy",
    )
    linked_service.connect()
    success, message = linked_service.test_connection()
    assert success is False
    assert message == "backend unhealthy"


def test_test_connection_uses_default_failure_message() -> None:
    """It uses a default reason when test_connection_ok is False."""
    linked_service = create_linked_service(test_connection_ok=False)
    success, message = linked_service.test_connection()
    assert success is False
    assert "health check failed" in message


def test_test_connection_fails_when_closed() -> None:
    """It returns False when the backend handle is closed but still attached."""
    linked_service = create_linked_service()
    linked_service.connect()
    linked_service.connection.close()
    success, message = linked_service.test_connection()
    assert success is False
    assert message == "connection is closed"
