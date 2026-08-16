"""
**File:** ``04_dataset_failure_resume.py``
**Region:** ``examples/04_dataset_failure_resume``

Example 04: Inject a mid-read failure and resume from checkpoint.

This example demonstrates how to:
- Fail on a configured page
- Persist pagination state
- Retry the same deterministic batch from the failed page
"""

from __future__ import annotations

import logging
from uuid import uuid4

from ds_common_logger_py_lib import Logger
from ds_resource_plugin_py_lib.common.resource.errors import ResourceException

from ds_provider_mock_py_lib.dataset import MockDataset, MockDatasetSettings
from ds_provider_mock_py_lib.linked_service import MockLinkedService, MockLinkedServiceSettings

Logger.configure(level=logging.DEBUG)
logger = Logger.get_logger(__name__)


def main() -> None:
    """Demonstrate failure injection and checkpoint resume."""
    linked_service = MockLinkedService(
        id=uuid4(),
        name="mock-linked-service",
        version="1.0.0",
        settings=MockLinkedServiceSettings(),
    )
    settings = MockDatasetSettings(row_count=30, page_size=10, raise_on_page=2)
    dataset = MockDataset(
        id=uuid4(),
        name="mock-dataset-resume",
        version="1.0.0",
        linked_service=linked_service,
        settings=settings,
    )

    try:
        linked_service.connect()
        try:
            dataset.read()
        except ResourceException as exc:
            logger.debug("Injected failure: %s checkpoint=%s", exc.message, dataset.checkpoint)

        settings.raise_on_page = None
        dataset.read()
        logger.debug(
            "Resumed rows=%s checkpoint=%s metadata=%s",
            len(dataset.output.index),
            dataset.checkpoint,
            dataset.operation.metadata,
        )
    finally:
        linked_service.close()


if __name__ == "__main__":
    main()
