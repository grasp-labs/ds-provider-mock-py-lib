"""
**File:** ``__init__.py``
**Region:** ``ds_provider_mock_py_lib/dataset``

Mock Dataset

This module implements a read-only synthetic dataset for e2e testing.

Example:
    >>> from uuid import uuid4
    >>> from ds_provider_mock_py_lib.dataset import MockDataset, MockDatasetSettings
    >>> from ds_provider_mock_py_lib.linked_service import MockLinkedService, MockLinkedServiceSettings
    >>> linked_service = MockLinkedService(
    ...     id=uuid4(),
    ...     name="mock-ls",
    ...     version="1.0.0",
    ...     settings=MockLinkedServiceSettings(),
    ... )
    >>> dataset = MockDataset(
    ...     id=uuid4(),
    ...     name="mock-ds",
    ...     version="1.0.0",
    ...     linked_service=linked_service,
    ...     settings=MockDatasetSettings(row_count=5),
    ... )
    >>> linked_service.connect()
    >>> dataset.read()
    >>> data = dataset.output
"""

from .mock import MockDataset
from .settings import MockColumn, MockDatasetSettings

__all__ = [
    "MockColumn",
    "MockDataset",
    "MockDatasetSettings",
]
