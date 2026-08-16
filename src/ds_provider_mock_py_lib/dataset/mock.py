"""
**File:** ``mock.py``
**Region:** ``ds_provider_mock_py_lib/dataset``

Mock read-only dataset for e2e testing with deterministic change batches.

The mock plays the role of a bronze-layer source. A full load emits the
initial snapshot; every incremental load emits one change batch whose
row-level composition is fully controlled by settings. Gold merge uses
primary key plus row hash: insert is a new key, update is an existing
key with changed values, and noop is an identical re-delivery.

Follows ``DATASET_CONTRACT.md``. Field classification:
    exposed  : id, name, description, version, settings, linked_service,
               serializer, deserializer
    internal : input, output, operation, checkpoint (base-class runtime fields)

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
    >>> len(dataset.output.index)
    5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NoReturn

from ds_common_logger_py_lib import Logger
from ds_resource_plugin_py_lib.common.resource.dataset import (
    DatasetStorageFormatType,
    TabularDataset,
)
from ds_resource_plugin_py_lib.common.resource.dataset.errors import ReadError
from ds_resource_plugin_py_lib.common.resource.errors import NotSupportedError, ResourceException
from ds_resource_plugin_py_lib.common.resource.linked_service.errors import ConnectionError
from ds_resource_plugin_py_lib.common.serde.deserialize import PandasDeserializer
from ds_resource_plugin_py_lib.common.serde.serialize import PandasSerializer

from ..enums import ResourceType
from ..errors import MockBackendError
from ..linked_service.mock import MockLinkedService
from .engines.read import ReadEngine
from .settings import MockDatasetSettings

logger = Logger.get_logger(__name__, package=True)


@dataclass(kw_only=True)
class MockDataset(
    TabularDataset[MockLinkedService, MockDatasetSettings, PandasSerializer, PandasDeserializer],
):
    """Read-only tabular dataset that emits deterministic synthetic rows."""

    linked_service: MockLinkedService
    settings: MockDatasetSettings
    serializer: PandasSerializer | None = field(
        default_factory=lambda: PandasSerializer(format=DatasetStorageFormatType.JSON),
    )
    deserializer: PandasDeserializer | None = field(
        default_factory=lambda: PandasDeserializer(format=DatasetStorageFormatType.JSON),
    )

    def __post_init__(self) -> None:
        """Ensure serializer and deserializer are always available."""
        if self.serializer is None:
            self.serializer = PandasSerializer(format=DatasetStorageFormatType.JSON)
        if self.deserializer is None:
            self.deserializer = PandasDeserializer(format=DatasetStorageFormatType.JSON)

    @property
    def supports_checkpoint(self) -> bool:
        """
        Whether this dataset supports incremental loads via ``self.checkpoint``.

        Returns:
            bool: Always ``True`` for the mock provider.
        """
        return True

    @property
    def type(self) -> ResourceType:
        """
        Get the type of the dataset.

        Returns:
            ResourceType
        """
        return ResourceType.DATASET

    def read(self) -> None:
        """
        Read the current mock batch into ``self.output``.

        An empty checkpoint performs a full load (batch 0). A populated
        incremental watermark reads the next change batch. A pagination cursor
        resumes an in-flight batch after failure.

        Raises:
            ReadError: If the mock backend fails or settings are invalid for read.
            ConnectionError: If dataset-level injection is configured as a connection error.
        """
        logger.debug("Reading mock dataset %s", self.name)
        try:
            connection = self.linked_service.connection
        except ConnectionError as exc:
            raise ReadError(
                message=f"Failed to read mock dataset: {exc.message}",
                status_code=exc.status_code,
                details={"provider": self.type.value, **exc.details},
            ) from exc

        reader = ReadEngine(
            connection=connection,
            settings=self.settings,
            dataset_name=self.name,
            provider_type=self.type.value,
        )
        try:
            reader.execute(checkpoint=self.checkpoint)
        except ResourceException:
            raise
        except MockBackendError as exc:
            raise ReadError(
                message=f"Failed to read mock dataset: {exc}",
                code=exc.code,
                status_code=exc.status_code,
                details={"provider": self.type.value, "dataset": self.name},
            ) from exc
        except Exception as exc:
            raise ReadError(
                message=f"Failed to read mock dataset: {exc}",
                details={"provider": self.type.value, "dataset": self.name},
            ) from exc
        finally:
            self.output = reader.output
            self.checkpoint = reader.checkpoint.serialize()
            self.operation.metadata = reader.metadata

    def create(self) -> NoReturn:
        """Create is not supported by this dataset."""
        self._unsupported("create")

    def update(self) -> NoReturn:
        """Update is not supported by this dataset."""
        self._unsupported("update")

    def upsert(self) -> NoReturn:
        """Upsert is not supported by this dataset."""
        self._unsupported("upsert")

    def delete(self) -> NoReturn:
        """Delete is not supported by this dataset."""
        self._unsupported("delete")

    def purge(self) -> NoReturn:
        """Purge is not supported by this dataset."""
        self._unsupported("purge")

    def rename(self) -> NoReturn:
        """Rename is not supported by this dataset."""
        self._unsupported("rename")

    def list(self) -> NoReturn:
        """List is not supported by this dataset."""
        self._unsupported("list")

    def close(self) -> None:
        """Close the dataset and underlying linked service."""
        logger.debug("Closing mock dataset linked service for %s", self.name)
        self.linked_service.close()

    def _unsupported(self, method: str) -> NoReturn:
        """
        Raise ``NotSupportedError`` for a read-only method.

        Args:
            method: Dataset method name.

        Raises:
            NotSupportedError: Always.
        """
        raise NotSupportedError(
            message=f"Method '{method}' is not supported by this provider.",
            details={"method": method, "provider": self.type.value, "dataset": self.name},
        )
