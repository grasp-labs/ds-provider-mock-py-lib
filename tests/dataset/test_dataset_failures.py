"""
**File:** ``test_dataset_failures.py``
**Region:** ``tests/dataset/test_dataset_failures``

MockDataset failure injection and resume tests.
"""

from __future__ import annotations

import pytest
from ds_resource_plugin_py_lib.common.resource.dataset.errors import ReadError
from ds_resource_plugin_py_lib.common.resource.linked_service.errors import ConnectionError

from ds_provider_mock_py_lib.enums import RaiseAs
from ds_provider_mock_py_lib.models import MockError
from tests.mocks import create_dataset, create_linked_service


def test_raise_on_page_read_error_saves_pagination() -> None:
    """It raises ReadError and keeps pagination so a retry can resume."""
    dataset = create_dataset(row_count=30, page_size=10, raise_on_page=2)
    with pytest.raises(ReadError) as exc_info:
        dataset.read()
    assert exc_info.value.code == "mock_read_failure"
    assert len(dataset.output.index) == 10
    assert dataset.checkpoint["pagination"]["value"] == "0:2"
    assert dataset.checkpoint["incremental"]["value"] is None
    assert dataset.operation.success is False


def test_resume_replays_from_failed_page() -> None:
    """It resumes the same batch from the failed page after clearing the inject."""
    dataset = create_dataset(row_count=30, page_size=10, raise_on_page=2)
    with pytest.raises(ReadError):
        dataset.read()
    dataset.settings.raise_on_page = None
    dataset.read()
    assert len(dataset.output.index) == 20
    assert dataset.checkpoint["incremental"]["value"] == 0
    assert dataset.checkpoint["pagination"]["value"] is None
    assert dataset.operation.metadata["resumed"] is True


def test_raise_as_connection_error() -> None:
    """It can inject a mid-read ConnectionError."""
    dataset = create_dataset(
        row_count=10,
        page_size=5,
        raise_on_page=1,
        raise_as=RaiseAs.CONNECTION_ERROR,
        raise_error=MockError(message="socket closed", code="lost", status_code=503),
    )
    with pytest.raises(ConnectionError) as exc_info:
        dataset.read()
    assert exc_info.value.code == "lost"
    assert dataset.checkpoint["pagination"]["value"] == "0:1"


def test_linked_service_fail_on_call_is_wrapped() -> None:
    """It wraps linked-service request failures as ReadError."""
    linked_service = create_linked_service(fail_on_call=1)
    dataset = create_dataset(linked_service=linked_service, row_count=5, page_size=2)
    with pytest.raises(ReadError) as exc_info:
        dataset.read()
    assert "call #1" in exc_info.value.message
    assert dataset.checkpoint["pagination"]["value"] == "0:1"


def test_invalid_checkpoint_payload_raises_read_error() -> None:
    """It raises ReadError when checkpoint cannot be deserialized."""
    dataset = create_dataset(row_count=1)
    dataset.checkpoint = {"pagination": "not-an-object"}  # type: ignore[assignment]
    with pytest.raises(ReadError, match="Invalid checkpoint"):
        dataset.read()


def test_invalid_pagination_cursor_raises_read_error() -> None:
    """It raises ReadError when a stored pagination cursor is malformed."""
    dataset = create_dataset(row_count=4, page_size=2)
    dataset.checkpoint = {
        "incremental": {"value": None},
        "pagination": {"value": "bad-cursor"},
    }
    with pytest.raises(ReadError, match="Invalid pagination cursor"):
        dataset.read()


def test_non_integer_pagination_cursor_raises_read_error() -> None:
    """It raises ReadError when pagination cursor parts are not integers."""
    dataset = create_dataset(row_count=4, page_size=2)
    dataset.checkpoint = {
        "incremental": {"value": None},
        "pagination": {"value": "a:b"},
    }
    with pytest.raises(ReadError, match="Invalid pagination cursor"):
        dataset.read()


def test_unexpected_backend_exception_is_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    """It wraps unexpected exceptions from the read engine as ReadError."""

    def explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "ds_provider_mock_py_lib.dataset.mock.ReadEngine.execute",
        explode,
    )
    dataset = create_dataset(row_count=1)
    with pytest.raises(ReadError, match="boom"):
        dataset.read()
