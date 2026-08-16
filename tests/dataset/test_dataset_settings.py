"""
**File:** ``test_dataset_settings.py``
**Region:** ``tests/dataset/test_dataset_settings``

MockDataset settings and initialization tests.
"""

from __future__ import annotations

from uuid import uuid4

from ds_provider_mock_py_lib.dataset import MockColumn, MockDataset, MockDatasetSettings
from ds_provider_mock_py_lib.enums import ColumnKind, ResourceType
from tests.mocks import create_dataset, create_linked_service


def test_dataset_type_is_dataset() -> None:
    """It exposes dataset type."""
    dataset = create_dataset(connect=False)
    assert dataset.type == ResourceType.DATASET
    assert dataset.supports_checkpoint is True


def test_settings_initialization() -> None:
    """It initializes settings with default values."""
    settings = MockDatasetSettings()
    assert settings.row_count == 100
    assert settings.page_size is None
    assert settings.seed == 42
    assert settings.op_column is None
    assert settings.modified_at_column == "_modified_at"
    assert settings.columns[0].kind == ColumnKind.SEQUENCE


def test_post_init_fills_missing_serde() -> None:
    """It installs default serializer and deserializer when omitted."""
    dataset = MockDataset(
        id=uuid4(),
        name="test-dataset",
        version="1.0.0",
        linked_service=create_linked_service(),
        settings=MockDatasetSettings(row_count=1),
        serializer=None,
        deserializer=None,
    )
    assert dataset.serializer is not None
    assert dataset.deserializer is not None


def test_deserialize_round_trip() -> None:
    """It deserializes a schema-valid dataset payload including nested linked service."""
    linked_service_id = str(uuid4())
    payload = {
        "id": str(uuid4()),
        "name": "mock-ds",
        "version": "1.0.0",
        "description": "e2e source",
        "settings": {
            "row_count": 8,
            "incremental_insert_count": 1,
            "columns": [{"name": "id", "kind": "sequence"}],
        },
        "linked_service": {
            "id": linked_service_id,
            "name": "mock-ls",
            "version": "1.0.0",
            "settings": {},
        },
        "serializer": None,
        "deserializer": None,
    }
    dataset = MockDataset.deserialize(payload)
    assert dataset.name == "mock-ds"
    assert dataset.settings.row_count == 8
    assert dataset.settings.incremental_insert_count == 1
    assert dataset.linked_service.name == "mock-ls"
    assert isinstance(dataset.settings.columns[0], MockColumn)
