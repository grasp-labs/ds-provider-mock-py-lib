"""
**File:** ``test_schema_contract.py``
**Region:** ``tests/dataset/test_schema_contract``

Schema and dataclass alignment tests.
"""

from __future__ import annotations

import json
from importlib.resources import files
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator

from ds_provider_mock_py_lib.dataset import MockDataset
from ds_provider_mock_py_lib.linked_service import MockLinkedService


def _load_schema(name: str) -> dict[str, object]:
    return json.loads(files("ds_provider_mock_py_lib").joinpath(name).read_text(encoding="utf-8"))


def test_linked_service_schema_valid_payload_constructs() -> None:
    """A schema-valid linked service payload constructs via deserialize()."""
    schema = _load_schema("schema.linked_service.json")
    payload = {
        "id": str(uuid4()),
        "name": "mock-ls",
        "version": "1.0.0",
        "settings": {"connect_behaviour": "ok"},
    }
    Draft202012Validator(schema).validate(payload)
    linked_service = MockLinkedService.deserialize(payload)
    assert linked_service.name == "mock-ls"


def test_linked_service_schema_rejects_unknown_keys() -> None:
    """It rejects unknown top-level linked service keys."""
    schema = _load_schema("schema.linked_service.json")
    payload = {
        "id": str(uuid4()),
        "name": "mock-ls",
        "version": "1.0.0",
        "settings": {},
        "unexpected": True,
    }
    with pytest.raises(Exception, match="unexpected"):
        Draft202012Validator(schema).validate(payload)


def test_dataset_schema_valid_payload_constructs() -> None:
    """A schema-valid dataset payload constructs via deserialize()."""
    schema = _load_schema("schema.dataset.json")
    payload = {
        "id": str(uuid4()),
        "name": "mock-ds",
        "version": "1.0.0",
        "settings": {
            "row_count": 3,
            "columns": [{"name": "id", "kind": "sequence"}],
        },
        "linked_service": {
            "id": str(uuid4()),
            "name": "mock-ls",
            "version": "1.0.0",
            "settings": {},
        },
        "serializer": None,
        "deserializer": None,
    }
    Draft202012Validator(schema).validate(payload)
    dataset = MockDataset.deserialize(payload)
    assert dataset.settings.row_count == 3


def test_dataset_schema_rejects_unknown_settings_keys() -> None:
    """It rejects unknown settings keys."""
    schema = _load_schema("schema.dataset.json")
    payload = {
        "id": str(uuid4()),
        "name": "mock-ds",
        "version": "1.0.0",
        "settings": {"row_count": 1, "not_a_field": True},
        "linked_service": {
            "id": str(uuid4()),
            "name": "mock-ls",
            "version": "1.0.0",
            "settings": {},
        },
    }
    with pytest.raises(Exception, match="not_a_field"):
        Draft202012Validator(schema).validate(payload)
