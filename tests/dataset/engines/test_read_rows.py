"""
**File:** ``test_read_rows.py``
**Region:** ``tests/dataset/engines/test_read_rows``

Deterministic batch generation tests.
"""

from __future__ import annotations

import pandas as pd
import pytest
from ds_resource_plugin_py_lib.common.resource.dataset.errors import ReadError

from ds_provider_mock_py_lib.dataset.engines._read_rows import _cell, build_batch_rows
from ds_provider_mock_py_lib.dataset.settings import MockColumn, MockDatasetSettings
from ds_provider_mock_py_lib.enums import ColumnKind, RowOp


def test_full_load_rows_are_inserts() -> None:
    """Batch 0 emits insert rows equal to row_count without an op column."""
    frame, ops = build_batch_rows(settings=MockDatasetSettings(row_count=4), batch=0)
    assert len(frame.index) == 4
    assert ops == [RowOp.INSERT] * 4
    assert "_op" not in frame.columns


def test_incremental_batch_is_deterministic() -> None:
    """The same settings produce the same incremental batch twice."""
    settings = MockDatasetSettings(
        row_count=15,
        incremental_insert_count=2,
        incremental_update_count=2,
        incremental_noop_count=1,
        seed=99,
        columns=[
            MockColumn(name="id", kind=ColumnKind.SEQUENCE),
            MockColumn(name="name", kind=ColumnKind.TEXT, prefix="n-"),
            MockColumn(name="score", kind=ColumnKind.RANDOM_FLOAT, low=0, high=1),
        ],
    )
    first_frame, first_ops = build_batch_rows(settings=settings, batch=1)
    second_frame, second_ops = build_batch_rows(settings=settings, batch=1)
    pd.testing.assert_frame_equal(first_frame, second_frame)
    assert first_ops == second_ops


def test_incremental_row_kinds_follow_pk_and_hash() -> None:
    """Insert is a new PK; update changes values; noop keeps last-known values."""
    settings = MockDatasetSettings(
        row_count=10,
        incremental_insert_count=2,
        incremental_update_count=2,
        incremental_noop_count=2,
        columns=[
            MockColumn(name="id", kind=ColumnKind.SEQUENCE),
            MockColumn(name="name", kind=ColumnKind.TEXT, prefix="n-"),
        ],
    )
    snapshot, _ = build_batch_rows(settings=settings, batch=0)
    incremental, ops = build_batch_rows(settings=settings, batch=1)
    assert ops == [RowOp.INSERT] * 2 + [RowOp.UPDATE] * 2 + [RowOp.NOOP] * 2
    snapshot_by_id = {int(row["id"]): row.drop(labels=["id"]).to_dict() for _, row in snapshot.iterrows()}
    for row, op in zip(incremental.to_dict("records"), ops, strict=True):
        row_id = int(row["id"])
        payload = {key: value for key, value in row.items() if key != "id"}
        if op == RowOp.INSERT:
            assert row_id not in snapshot_by_id
            continue
        assert row_id in snapshot_by_id
        if op == RowOp.UPDATE:
            assert payload != snapshot_by_id[row_id]
        else:
            assert payload == snapshot_by_id[row_id]


def test_enum_column_picks_from_provided_values() -> None:
    """Enum cells are members of the configured values list and are deterministic."""
    column = MockColumn(
        name="status",
        kind=ColumnKind.ENUM,
        value=["active", "deactive"],
    )
    settings = MockDatasetSettings(columns=[MockColumn(name="id", kind=ColumnKind.SEQUENCE), column], row_count=20)
    frame, _ops = build_batch_rows(settings=settings, batch=0)
    assert set(frame["status"].tolist()).issubset({"active", "deactive"})
    assert _cell(settings=settings, column=column, row_id=3, version=0) == _cell(
        settings=settings,
        column=column,
        row_id=3,
        version=0,
    )


def test_enum_column_requires_values() -> None:
    """It raises ReadError when enum kind has an empty values list."""
    column = MockColumn(name="status", kind=ColumnKind.ENUM)
    with pytest.raises(ReadError, match="non-empty list in value"):
        _cell(settings=MockDatasetSettings(), column=column, row_id=1, version=0)


def test_unknown_column_kind_raises() -> None:
    """It raises ReadError when a column kind is not implemented."""
    column = MockColumn(name="weird", kind=ColumnKind.TEXT)
    object.__setattr__(column, "kind", "not-a-kind")
    with pytest.raises(ReadError, match="unknown column kind"):
        _cell(settings=MockDatasetSettings(), column=column, row_id=1, version=0)
