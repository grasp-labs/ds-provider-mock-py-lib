"""
**File:** ``test_resource_yaml.py``
**Region:** ``tests/test_resource_yaml``

Provider discovery metadata tests.
"""

from __future__ import annotations

from importlib.resources import files

import yaml
from ds_resource_plugin_py_lib.common.resource.client import ResourceClient

from ds_provider_mock_py_lib.enums import ResourceType


def test_resource_yaml_declares_mock_linked_service_and_dataset() -> None:
    """It ships a resource.yaml that ResourceClient can parse."""
    payload = yaml.safe_load(files("ds_provider_mock_py_lib").joinpath("resource.yaml").read_text(encoding="utf-8"))
    assert payload["name"] == "mock"
    assert payload["linked_service"][0]["type"] == ResourceType.LINKED_SERVICE
    assert payload["dataset"][0]["type"] == ResourceType.DATASET
    assert payload["linked_service"][0]["class_name"].endswith("MockLinkedService")
    assert payload["dataset"][0]["class_name"].endswith("MockDataset")


def test_resource_client_discovers_mock_provider() -> None:
    """It is discoverable through the ds.providers entry point."""
    client = ResourceClient()
    assert (ResourceType.DATASET.value, "1.0.0") in client.datasets
    assert (ResourceType.LINKED_SERVICE.value, "1.0.0") in client.linked_services
