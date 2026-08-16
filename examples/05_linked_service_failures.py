"""
**File:** ``05_linked_service_failures.py``
**Region:** ``examples/05_linked_service_failures``

Example 05: Scripted linked-service connect and health-check failures.

Catalog JSON is deserialized into models. Enums are lowercase strings
(``authentication_error``) and nested errors are plain objects, not
``MockError`` / ``ConnectBehaviour`` instances.

This example demonstrates how to:
- Raise ``ConnectionError``, ``AuthenticationError``, and ``AuthorizationError``
- Fail the first N ``connect()`` attempts, then succeed
- Fail ``test_connection()`` without raising
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from ds_common_logger_py_lib import Logger
from ds_resource_plugin_py_lib.common.resource.errors import ResourceException
from ds_resource_plugin_py_lib.common.resource.linked_service.errors import ConnectionError

from ds_provider_mock_py_lib.linked_service import MockLinkedService

Logger.configure(level=logging.DEBUG)
logger = Logger.get_logger(__name__)


def _linked_service(settings: dict[str, Any]) -> MockLinkedService:
    """
    Build a mock linked service from a catalog JSON payload.

    Args:
        settings: JSON object for ``settings`` (string enums, nested error objects).

    Returns:
        An unconnected ``MockLinkedService``.

    Example:
        >>> linked_service = _linked_service({"connect_behaviour": "ok"})
        >>> linked_service.settings.connect_behaviour
        'ok'
    """
    return MockLinkedService.deserialize(
        {
            "id": str(uuid4()),
            "name": "mock-linked-service",
            "version": "1.0.0",
            "settings": settings,
        }
    )


def _try_connect(label: str, settings: dict[str, Any]) -> None:
    """
    Attempt ``connect()`` and log the contract error, if any.

    Args:
        label: Scenario name written to the log.
        settings: JSON object for ``settings``.
    """
    linked_service = _linked_service(settings)
    try:
        linked_service.connect()
        logger.debug("%s: connected", label)
    except ResourceException as exc:
        logger.debug(
            "%s: raised %s message=%s code=%s status=%s",
            label,
            type(exc).__name__,
            exc.message,
            exc.code,
            exc.status_code,
        )
    finally:
        linked_service.close()


def main() -> None:
    """Run connect-failure and health-check scenarios from JSON payloads."""
    _try_connect(
        "connection_error",
        {
            "connect_behaviour": "connection_error",
            "connect_error": {
                "message": "cannot reach backend",
                "code": "DS_CONNECTION_ERROR",
                "status_code": 503,
            },
        },
    )
    _try_connect(
        "authentication_error",
        {
            "connect_behaviour": "authentication_error",
            "connect_error": {
                "message": "bad token",
                "code": "DS_AUTHENTICATION_ERROR",
                "status_code": 401,
            },
        },
    )
    _try_connect(
        "authorization_error",
        {
            "connect_behaviour": "authorization_error",
            "connect_error": {
                "message": "role missing",
                "code": "DS_AUTHORIZATION_ERROR",
                "status_code": 403,
            },
        },
    )

    transient = _linked_service({"connect_fail_first_n": 2})
    try:
        for attempt in range(1, 4):
            try:
                transient.connect()
                logger.debug("transient: connected on attempt %s", attempt)
                break
            except ConnectionError as exc:
                logger.debug("transient: attempt %s failed: %s", attempt, exc.message)
    finally:
        transient.close()

    health = _linked_service(
        {
            "test_connection_ok": False,
            "test_connection_message": "backend unhealthy",
        }
    )
    try:
        health.connect()
        success, message = health.test_connection()
        logger.debug("test_connection: success=%s message=%s", success, message)
    finally:
        health.close()


if __name__ == "__main__":
    main()
