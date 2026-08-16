"""
**File:** ``test_linked_service_settings.py``
**Region:** ``tests/linked_service/test_linked_service_settings``

MockLinkedService settings and initialization tests.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from ds_resource_plugin_py_lib.common.resource.linked_service.errors import ConnectionError

from ds_provider_mock_py_lib.enums import ConnectBehaviour, ResourceType
from ds_provider_mock_py_lib.linked_service import MockLinkedService, MockLinkedServiceSettings
from ds_provider_mock_py_lib.models import MockError


def test_linked_service_type_is_linked_service() -> None:
    """It exposes linked service type."""
    linked_service = MockLinkedService(
        id=uuid4(),
        name="test-linked-service",
        version="1.0.0",
        settings=MockLinkedServiceSettings(),
    )
    assert linked_service.type == ResourceType.LINKED_SERVICE


def test_connection_raises_before_connect() -> None:
    """It raises ConnectionError for connection property before connect()."""
    linked_service = MockLinkedService(
        id=uuid4(),
        name="test-linked-service",
        version="1.0.0",
        settings=MockLinkedServiceSettings(),
    )
    with pytest.raises(ConnectionError):
        _ = linked_service.connection


def test_settings_initialization() -> None:
    """It initializes settings with default values."""
    settings = MockLinkedServiceSettings()
    assert settings.connect_behaviour == ConnectBehaviour.OK
    assert settings.connect_delay_ms == 0
    assert settings.connect_fail_first_n == 0
    assert settings.test_connection_ok is True
    assert settings.fail_on_call is None
    assert settings.drop_after_calls is None
    assert isinstance(settings.connect_error, MockError)


def test_deserialize_round_trip() -> None:
    """It deserializes a schema-valid linked service payload."""
    payload = {
        "id": str(uuid4()),
        "name": "mock-ls",
        "version": "1.0.0",
        "description": None,
        "settings": {
            "connect_behaviour": "ok",
            "connect_fail_first_n": 1,
        },
    }
    linked_service = MockLinkedService.deserialize(payload)
    assert linked_service.name == "mock-ls"
    assert linked_service.settings.connect_fail_first_n == 1
    assert linked_service.serialize()["settings"]["connect_behaviour"] == "ok"
