"""
**File:** ``07_dataset_backend_failures.py``
**Region:** ``examples/07_dataset_backend_failures``

Example 07: Linked-service request failures surfaced through ``dataset.read()``.

Catalog JSON is deserialized into models. ``fail_on_call`` / ``drop_after_calls``
and nested ``request_error`` / ``drop_error`` objects are JSON, not Python models.

This example demonstrates how to:
- Fail on the Nth backend ``request()`` call
- Drop the connection after N successful calls
- See both wrapped as ``ReadError`` with pagination saved for resume
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from ds_common_logger_py_lib import Logger
from ds_resource_plugin_py_lib.common.resource.errors import ResourceException

from ds_provider_mock_py_lib.dataset import MockDataset

Logger.configure(level=logging.DEBUG)
logger = Logger.get_logger(__name__)


def _dataset(name: str, linked_service_settings: dict[str, Any]) -> MockDataset:
    """
    Build a mock dataset whose linked service is deserialized from JSON.

    Args:
        name: Dataset name.
        linked_service_settings: JSON object for linked-service ``settings``.

    Returns:
        A ``MockDataset`` ready for ``connect()`` / ``read()``.

    Example:
        >>> dataset = _dataset("mock-ds", {"fail_on_call": 1})
        >>> dataset.linked_service.settings.fail_on_call
        1
    """
    return MockDataset.deserialize(
        {
            "id": str(uuid4()),
            "name": name,
            "version": "1.0.0",
            "settings": {"row_count": 30, "page_size": 10},
            "linked_service": {
                "id": str(uuid4()),
                "name": "mock-linked-service",
                "version": "1.0.0",
                "settings": linked_service_settings,
            },
            "serializer": None,
            "deserializer": None,
        }
    )


def _run_backend_failure(label: str, linked_service_settings: dict[str, Any]) -> None:
    """
    Read a paged snapshot until the backend failure rule matches.

    Args:
        label: Scenario name written to the log.
        linked_service_settings: JSON object for linked-service ``settings``.
    """
    dataset = _dataset(f"mock-dataset-{label}", linked_service_settings)
    try:
        dataset.linked_service.connect()
        dataset.read()
        logger.debug("%s: unexpected success", label)
    except ResourceException as exc:
        logger.debug(
            "%s: raised %s message=%s code=%s status=%s rows=%s checkpoint=%s calls=%s",
            label,
            type(exc).__name__,
            exc.message,
            exc.code,
            exc.status_code,
            len(dataset.output.index),
            dataset.checkpoint,
            dataset.linked_service.connection.call_count,
        )
    finally:
        dataset.linked_service.close()


def main() -> None:
    """Run ``fail_on_call`` and ``drop_after_calls`` scenarios from JSON payloads."""
    _run_backend_failure(
        "fail_on_call",
        {
            "fail_on_call": 2,
            "request_error": {
                "message": "mock backend failure",
                "code": "DS_BACKEND_ERROR",
                "status_code": 500,
            },
        },
    )
    _run_backend_failure(
        "drop_after_calls",
        {
            "drop_after_calls": 1,
            "drop_error": {
                "message": "connection dropped",
                "code": "DS_CONNECTION_ERROR",
                "status_code": 502,
            },
        },
    )


if __name__ == "__main__":
    main()
