"""
**File:** ``test_dataset_read.py``
**Region:** ``tests/dataset/test_dataset_read``

MockDataset read() method tests.
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest
from ds_resource_plugin_py_lib.common.resource.dataset.errors import ReadError

from ds_provider_mock_py_lib.dataset import MockColumn
from ds_provider_mock_py_lib.enums import ColumnKind, RowOp
from tests.mocks import create_dataset, create_linked_service


def test_read_raises_when_connection_is_missing() -> None:
    """It wraps a missing connection as ReadError."""
    dataset = create_dataset(connect=False, row_count=1)
    with pytest.raises(ReadError) as exc_info:
        dataset.read()
    assert "not connected" in exc_info.value.message.lower()


def test_read_full_load_emits_inserts() -> None:
    """It emits row_count insert rows on an empty checkpoint."""
    dataset = create_dataset(row_count=12, page_size=5)
    dataset.read()
    assert len(dataset.output.index) == 12
    assert "_op" not in dataset.output.columns
    assert dataset.operation.metadata["ops"] == {RowOp.INSERT: 12}
    assert dataset.checkpoint["incremental"]["value"] == 0
    assert dataset.checkpoint["pagination"]["value"] is None
    assert dataset.operation.success is True
    assert dataset.operation.row_count == 12
    assert dataset.operation.metadata["batch"] == 0


def test_read_empty_full_load() -> None:
    """It returns an empty frame for a zero-row snapshot."""
    dataset = create_dataset(row_count=0)
    dataset.read()
    assert dataset.output.empty
    assert dataset.checkpoint["incremental"]["value"] == 0


def test_read_is_deterministic() -> None:
    """It emits identical rows for the same settings and seed."""
    first = create_dataset(
        row_count=7,
        columns=[
            MockColumn(name="id", kind=ColumnKind.SEQUENCE),
            MockColumn(name="amount", kind=ColumnKind.RANDOM_INT, low=1, high=50),
            MockColumn(name="flag", kind=ColumnKind.BOOL),
            MockColumn(name="ts", kind=ColumnKind.TIMESTAMP),
            MockColumn(name="label", kind=ColumnKind.CONSTANT, value="x"),
        ],
        seed=7,
    )
    first.read()
    second = create_dataset(row_count=7, columns=list(first.settings.columns), seed=7)
    second.read()
    pd.testing.assert_frame_equal(first.output, second.output)


def test_read_null_every_is_stable_by_id() -> None:
    """It nulls the same ids across reruns."""
    dataset = create_dataset(
        row_count=6,
        columns=[
            MockColumn(name="id", kind=ColumnKind.SEQUENCE),
            MockColumn(name="name", kind=ColumnKind.TEXT, prefix="row_", null_every=2),
        ],
    )
    dataset.read()
    null_ids = dataset.output.loc[dataset.output["name"].isna(), "id"].tolist()
    assert null_ids == [0, 2, 4]


def test_read_incremental_empty_batch() -> None:
    """It advances the watermark with no rows when incremental counts are zero."""
    dataset = create_dataset(row_count=4)
    dataset.read()
    dataset.checkpoint = dataset.checkpoint
    dataset.read()
    assert dataset.output.empty
    assert dataset.checkpoint["incremental"]["value"] == 1
    assert dataset.operation.metadata["ops"] == {}


def test_read_incremental_change_batch() -> None:
    """Insert is a new PK, update changes hash, noop keeps hash."""
    dataset = create_dataset(
        row_count=20,
        incremental_insert_count=3,
        incremental_update_count=2,
        incremental_noop_count=2,
        columns=[
            MockColumn(name="id", kind=ColumnKind.SEQUENCE),
            MockColumn(name="tag", kind=ColumnKind.TEXT, prefix="t-"),
        ],
    )
    dataset.read()
    snapshot = dataset.output.copy()
    snapshot_ids = set(snapshot["id"].tolist())
    dataset.checkpoint = dataset.checkpoint
    dataset.read()

    assert dataset.operation.metadata["ops"] == {
        RowOp.INSERT: 3,
        RowOp.UPDATE: 2,
        RowOp.NOOP: 2,
    }
    incremental = dataset.output
    new_ids = set(incremental["id"].tolist()) - snapshot_ids
    assert len(new_ids) == 3

    existing_ids = [int(row_id) for row_id in incremental["id"].tolist() if row_id in snapshot_ids]
    identical_ids: list[int] = []
    changed_ids: list[int] = []
    for row_id in existing_ids:
        current = incremental.loc[incremental["id"] == row_id].iloc[0]
        prior = snapshot.loc[snapshot["id"] == row_id].iloc[0]
        if current.to_dict() == prior.to_dict():
            identical_ids.append(row_id)
        else:
            changed_ids.append(row_id)
            assert current["tag"] != prior["tag"]

    assert len(changed_ids) == 2
    assert len(identical_ids) == 2


def test_read_second_incremental_replays_prior_batch_state() -> None:
    """A second incremental batch replays prior live-set mutations deterministically."""
    dataset = create_dataset(
        row_count=20,
        incremental_insert_count=2,
        incremental_update_count=2,
        incremental_noop_count=1,
        columns=[
            MockColumn(name="id", kind=ColumnKind.SEQUENCE),
            MockColumn(name="tag", kind=ColumnKind.TEXT, prefix="t-"),
        ],
    )
    dataset.read()
    dataset.read()
    first_incremental_ids = set(dataset.output["id"].tolist())
    dataset.read()
    assert dataset.checkpoint["incremental"]["value"] == 2
    assert len(dataset.output.index) == 5
    assert dataset.operation.metadata["ops"][RowOp.INSERT] == 2
    batch2_new_ids = set(dataset.output["id"].tolist()) - set(range(20)) - first_incremental_ids
    assert len(batch2_new_ids) == 2


def test_read_rejects_incremental_when_not_enough_live_rows() -> None:
    """It raises ReadError when a change batch needs more live rows than exist."""
    dataset = create_dataset(
        row_count=2,
        incremental_update_count=5,
    )
    dataset.read()
    with pytest.raises(ReadError) as exc_info:
        dataset.read()
    assert "needs 5 existing rows" in exc_info.value.message


@patch("ds_provider_mock_py_lib.dataset.engines.read.time.sleep")
def test_read_applies_page_delay(mock_sleep: object) -> None:
    """It sleeps after each successful page when page_delay_ms is set."""
    dataset = create_dataset(row_count=4, page_size=2, page_delay_ms=5)
    dataset.read()
    assert mock_sleep.call_count == 2  # type: ignore[attr-defined]


def test_read_rejects_invalid_page_size() -> None:
    """It raises ReadError for a non-positive page_size."""
    dataset = create_dataset(row_count=2)
    dataset.settings.page_size = 0
    with pytest.raises(ReadError, match="page_size"):
        dataset.read()


def test_read_rejects_negative_row_count() -> None:
    """It raises ReadError for a negative row_count."""
    dataset = create_dataset()
    dataset.settings.row_count = -1
    with pytest.raises(ReadError, match="row_count"):
        dataset.read()


def test_read_rejects_column_name_collision() -> None:
    """It raises when a reserved column collides with a configured column."""
    dataset = create_dataset(
        row_count=1,
        op_column="id",
        columns=[MockColumn(name="id", kind=ColumnKind.SEQUENCE)],
    )
    with pytest.raises(ReadError, match="must not collide"):
        dataset.read()


def test_optional_op_column_is_emitted_when_configured() -> None:
    """It adds the label column only when op_column is set."""
    dataset = create_dataset(row_count=3, op_column="row_kind")
    dataset.read()
    assert dataset.output["row_kind"].tolist() == [RowOp.INSERT] * 3
    assert dataset.operation.metadata["ops"] == {RowOp.INSERT: 3}


def test_read_rejects_duplicate_column_names() -> None:
    """It raises when column names are not unique."""
    dataset = create_dataset(
        row_count=1,
        columns=[
            MockColumn(name="id", kind=ColumnKind.SEQUENCE),
            MockColumn(name="id", kind=ColumnKind.TEXT),
        ],
    )
    with pytest.raises(ReadError, match="unique"):
        dataset.read()


def test_dataset_close_closes_linked_service() -> None:
    """It closes the linked service from dataset.close()."""
    linked_service = create_linked_service()
    dataset = create_dataset(linked_service=linked_service, row_count=1)
    dataset.close()
    with pytest.raises(ReadError):
        dataset.read()


def test_dataset_context_manager_closes() -> None:
    """It closes via the dataset context manager."""
    dataset = create_dataset(row_count=1)
    with dataset:
        dataset.read()
        assert dataset.linked_service.connection.closed is False
    with pytest.raises(ReadError):
        dataset.read()
