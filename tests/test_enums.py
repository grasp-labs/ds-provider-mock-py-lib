"""
**File:** ``test_enums.py``
**Region:** ``tests/test_enums``

ResourceType and mock enum tests.
"""

from __future__ import annotations

from ds_provider_mock_py_lib.enums import ColumnKind, ConnectBehaviour, RaiseAs, ResourceType, RowOp


def test_resource_type_linked_service_value() -> None:
    """It exposes the correct linked service type value."""
    assert ResourceType.LINKED_SERVICE == "ds.resource.linked-service.mock"
    assert isinstance(ResourceType.LINKED_SERVICE, str)


def test_resource_type_dataset_value() -> None:
    """It exposes the correct dataset type value."""
    assert ResourceType.DATASET == "ds.resource.dataset.mock"
    assert isinstance(ResourceType.DATASET, str)


def test_resource_type_enum_membership() -> None:
    """It allows checking enum membership."""
    assert ResourceType.LINKED_SERVICE in ResourceType
    assert ResourceType.DATASET in ResourceType


def test_resource_type_enum_comparison() -> None:
    """It supports equality comparison with strings."""
    assert ResourceType.LINKED_SERVICE == "ds.resource.linked-service.mock"
    assert ResourceType.DATASET == "ds.resource.dataset.mock"
    assert ResourceType.LINKED_SERVICE != ResourceType.DATASET


def test_supporting_enum_values_are_lowercase() -> None:
    """It uses lowercase identifier values."""
    assert ConnectBehaviour.OK == "ok"
    assert ColumnKind.SEQUENCE == "sequence"
    assert ColumnKind.ENUM == "enum"
    assert RowOp.INSERT == "insert"
    assert RaiseAs.READ_ERROR == "read_error"
    assert RaiseAs.CONNECTION_ERROR == "connection_error"
