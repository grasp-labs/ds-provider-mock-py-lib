"""
**File:** ``03_dataset_incremental.py``
**Region:** ``examples/03_dataset_incremental``

Example 03: Snapshot then CDC change batches.

This example demonstrates how to:
- Persist ``dataset.checkpoint`` between reads
- Emit insert / update / noop rows for gold merge via PK + hash
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
    """Demonstrate snapshot plus incremental CDC batches."""
    linked_service = MockLinkedService(
        id=uuid4(),
        name="mock-linked-service",
        version="1.0.0",
        settings=MockLinkedServiceSettings(),
    )
    dataset = MockDataset(
        id=uuid4(),
        name="mock-dataset-incremental",
        version="1.0.0",
        linked_service=linked_service,
        settings=MockDatasetSettings(
            columns=[
                MockColumn(name="id", kind=ColumnKind.SEQUENCE),
                MockColumn(name="tag", kind=ColumnKind.TEXT, prefix="t-"),
            ],
            row_count=50,
            incremental_insert_count=5,
            incremental_update_count=4,
            incremental_noop_count=3,
            page_size=20,
        ),
    )

    try:
        linked_service.connect()
        dataset.checkpoint = {}
        dataset.read()
        logger.debug("Snapshot rows=%s checkpoint=%s", len(dataset.output.index), dataset.checkpoint)

        snapshot_checkpoint = dataset.checkpoint
        dataset.checkpoint = snapshot_checkpoint
        dataset.read()
        logger.debug("Incremental ops=%s checkpoint=%s", dataset.operation.metadata.get("ops"), dataset.checkpoint)
    except ResourceException as exc:
        logger.error("Dataset incremental read failed: %s", exc.message)
        logger.error("Exception: %s", exc.__dict__)
    finally:
        linked_service.close()


if __name__ == "__main__":
    main()
