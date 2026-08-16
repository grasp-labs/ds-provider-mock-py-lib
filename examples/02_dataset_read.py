"""
**File:** ``02_dataset_read.py``
**Region:** ``examples/02_dataset_read``

Example 02: Full-load snapshot from the mock dataset.

This example demonstrates how to:
- Create and connect a mock linked service
- Create a mock dataset with synthetic columns
- Execute ``read()`` for batch 0 (all inserts)
"""

from __future__ import annotations

import logging
from uuid import uuid4

from ds_common_logger_py_lib import Logger
from ds_resource_plugin_py_lib.common.resource.errors import ResourceException

from ds_provider_mock_py_lib.dataset import MockColumn, MockDataset, MockDatasetSettings
from ds_provider_mock_py_lib.enums import ColumnKind
from ds_provider_mock_py_lib.linked_service import MockLinkedService, MockLinkedServiceSettings

Logger.configure(level=logging.DEBUG)
logger = Logger.get_logger(__name__)


def main() -> None:
    """Demonstrate a mock dataset full load."""
    linked_service = MockLinkedService(
        id=uuid4(),
        name="mock-linked-service",
        version="1.0.0",
        settings=MockLinkedServiceSettings(),
    )
    dataset = MockDataset(
        id=uuid4(),
        name="mock-dataset-read",
        version="1.0.0",
        linked_service=linked_service,
        settings=MockDatasetSettings(
            columns=[
                MockColumn(name="id", kind=ColumnKind.SEQUENCE),
                MockColumn(name="name", kind=ColumnKind.TEXT, prefix="row_"),
                MockColumn(name="amount", kind=ColumnKind.RANDOM_FLOAT, low=0, high=500),
            ],
            row_count=200,
            page_size=10,
        ),
    )

    try:
        linked_service.connect()
        dataset.read()
    except ResourceException as exc:
        logger.error("Dataset read failed: %s", exc.message)
        logger.error("Exception: %s", exc.__dict__)
    finally:
        linked_service.close()

    logger.debug("Rows: %s", len(dataset.output.index))
    logger.debug("Checkpoint: %s", dataset.checkpoint)
    logger.debug("Operation metadata: %s", dataset.operation.metadata)
    logger.debug("Output: %s", dataset.output)


if __name__ == "__main__":
    main()
