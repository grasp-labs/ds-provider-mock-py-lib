"""
**File:** ``06_dataset_raise_scenarios.py``
**Region:** ``examples/06_dataset_raise_scenarios``

Example 06: Dataset-level ``raise_on_page`` for each ``RaiseAs`` mode.

Catalog JSON is deserialized into models. ``raise_as`` is a lowercase
string and ``raise_error`` is a plain object, not ``RaiseAs`` / ``MockError``.

This example demonstrates how to:
- Inject ``ReadError`` on a configured page
- Inject ``ConnectionError`` mid-read
- Inspect pagination checkpoint state after each failure
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


def _dataset(name: str, settings: dict[str, Any]) -> MockDataset:
    """
    Build a mock dataset from a catalog JSON payload.

    Args:
        name: Dataset name.
        settings: JSON object for dataset ``settings``.

    Returns:
        A ``MockDataset`` with a nested deserialized linked service.

    Example:
        >>> dataset = _dataset("mock-ds", {"row_count": 1, "raise_on_page": 1})
        >>> dataset.settings.raise_on_page
        1
    """
    return MockDataset.deserialize(
        {
            "id": str(uuid4()),
            "name": name,
            "version": "1.0.0",
            "settings": settings,
            "linked_service": {
                "id": str(uuid4()),
                "name": "mock-linked-service",
                "version": "1.0.0",
                "settings": {},
            },
            "serializer": None,
            "deserializer": None,
        }
    )


def _run_raise_scenario(label: str, settings: dict[str, Any]) -> None:
    """
    Connect, read until the injected failure, and log the contract error.

    Args:
        label: Scenario name written to the log.
        settings: JSON object for dataset ``settings``.
    """
    dataset = _dataset(f"mock-dataset-{label}", {"row_count": 30, "page_size": 10, **settings})
    try:
        dataset.linked_service.connect()
        dataset.read()
        logger.debug("%s: unexpected success", label)
    except ResourceException as exc:
        logger.error(exc.__dict__)
        logger.debug(
            "%s: raised %s message=%s code=%s status=%s rows=%s checkpoint=%s",
            label,
            type(exc).__name__,
            exc.message,
            exc.code,
            exc.status_code,
            len(dataset.output.index),
            dataset.checkpoint,
        )
    finally:
        dataset.linked_service.close()


def main() -> None:
    """Run ``raise_on_page`` for every ``raise_as`` JSON value."""
    _run_raise_scenario(
        "raise_as_read_error",
        {
            "raise_on_page": 2,
            "raise_as": "read_error",
            "raise_error": {
                "message": "page 2 read failed",
                "code": "DS_READ_ERROR",
                "status_code": 500,
            },
        },
    )
    _run_raise_scenario(
        "raise_as_connection_error",
        {
            "raise_on_page": 1,
            "raise_as": "connection_error",
            "raise_error": {
                "message": "socket closed",
                "code": "DS_CONNECTION_ERROR",
                "status_code": 503,
            },
        },
    )


if __name__ == "__main__":
    main()
