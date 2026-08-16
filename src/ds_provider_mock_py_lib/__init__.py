"""
**File:** ``__init__.py``
**Region:** ``ds-provider-mock-py-lib``

Description
-----------
Mock provider for e2e pipeline testing. Read-only, fully deterministic,
deterministic change batches for gold merge via primary key and row hash.

Example
-------
.. code-block:: python

    from uuid import uuid4

    from ds_provider_mock_py_lib import (
        MockDataset,
        MockDatasetSettings,
        MockLinkedService,
        MockLinkedServiceSettings,
    )

    linked_service = MockLinkedService(
        id=uuid4(),
        name="mock-ls",
        version="1.0.0",
        settings=MockLinkedServiceSettings(),
    )
    dataset = MockDataset(
        id=uuid4(),
        name="mock-ds",
        version="1.0.0",
        linked_service=linked_service,
        settings=MockDatasetSettings(row_count=10),
    )
    linked_service.connect()
    dataset.read()
    print(len(dataset.output.index))
"""

from importlib.metadata import version

from .dataset import MockColumn, MockDataset, MockDatasetSettings
from .linked_service import MockLinkedService, MockLinkedServiceSettings

PACKAGE_NAME = "ds-provider-mock-py-lib"
__version__ = version(PACKAGE_NAME)

__all__ = [
    "MockColumn",
    "MockDataset",
    "MockDatasetSettings",
    "MockLinkedService",
    "MockLinkedServiceSettings",
    "__version__",
]
