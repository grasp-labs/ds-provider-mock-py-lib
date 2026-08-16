"""
**File:** ``_read_rows.py``
**Region:** ``ds_provider_mock_py_lib/dataset/engines``

Deterministic batch generation for mock reads.

Every id selection and cell value is a pure function of
``(settings.seed, id, version, batch)``. No hidden process state is used, so
reconnects and suite reruns produce the same rows.

Example:
    >>> from ds_provider_mock_py_lib.dataset.engines._read_rows import build_batch_rows
    >>> from ds_provider_mock_py_lib.dataset.settings import MockDatasetSettings
    >>> frame, ops = build_batch_rows(settings=MockDatasetSettings(row_count=3), batch=0)
    >>> [op.value for op in ops]
    ['insert', 'insert', 'insert']
    >>> "_op" in frame.columns
    False
"""

from __future__ import annotations

import hashlib
import random
from typing import TYPE_CHECKING, Any

import pandas as pd
from ds_resource_plugin_py_lib.common.resource.dataset.errors import ReadError

from ...enums import ColumnKind, RowOp

if TYPE_CHECKING:
    from ..settings import MockColumn, MockDatasetSettings


def _rng(*parts: int | str) -> random.Random:
    """
    Build a process-stable RNG from seed parts.

    Args:
        parts: Values mixed into the SHA-256 seed.

    Returns:
        A ``random.Random`` instance with a stable seed.
    """
    digest = hashlib.sha256()
    for part in parts:
        digest.update(f"{part}".encode())
        digest.update(b"\0")
    seed = int.from_bytes(digest.digest()[:8], "big")
    # Synthetic test data only; not used for security.
    return random.Random(seed)  # nosec B311


def replay_state(settings: MockDatasetSettings, batch: int) -> tuple[list[int], dict[int, int], int]:
    """
    Replay batches ``1..batch-1`` and return live ids, versions, and high-water mark.

    Args:
        settings: Dataset settings that define batch composition.
        batch: Batch about to be generated.

    Returns:
        ``(live_ids, id_to_version, high_water_mark)``.
    """
    live = list(range(settings.row_count))
    version: dict[int, int] = {}
    high_water_mark = settings.row_count
    for prior_batch in range(1, batch):
        inserts, updates, _noops = select_batch_ids(
            settings=settings,
            batch=prior_batch,
            live=live,
            high_water_mark=high_water_mark,
        )
        for row_id in updates:
            version[row_id] = prior_batch
        live.extend(inserts)
        for row_id in inserts:
            version[row_id] = prior_batch
        high_water_mark += len(inserts)
    return live, version, high_water_mark


def select_batch_ids(
    settings: MockDatasetSettings,
    batch: int,
    live: list[int],
    high_water_mark: int,
) -> tuple[list[int], list[int], list[int]]:
    """
    Deterministically pick insert, update, and noop ids for a batch.

    Args:
        settings: Dataset settings that define batch composition.
        batch: Batch number being generated.
        live: Currently live ids.
        high_water_mark: Next unused id.

    Returns:
        ``(inserts, updates, noops)``.

    Raises:
        ReadError: If the batch needs more live rows than exist.
    """
    needed = settings.incremental_update_count + settings.incremental_noop_count
    if needed > len(live):
        raise ReadError(
            message=(f"batch {batch} needs {needed} existing rows (updates+noops) but only {len(live)} are live"),
            code="invalid_settings",
            status_code=400,
            details={"batch": batch, "live": len(live), "needed": needed},
        )

    rng = _rng(settings.seed, 1_000_000 + batch)
    picked = rng.sample(live, needed) if needed else []
    update_count = settings.incremental_update_count
    updates = [int(row_id) for row_id in picked[:update_count]]
    noops = [int(row_id) for row_id in picked[update_count:]]
    inserts = list(range(high_water_mark, high_water_mark + settings.incremental_insert_count))
    return inserts, updates, noops


def build_batch_rows(settings: MockDatasetSettings, batch: int) -> tuple[pd.DataFrame, list[RowOp]]:
    """
    Build the ordered row set for a batch: inserts, updates, noops.

    Insert adds a new primary key. Update reuses a live key with changed
    values so the row hash changes. Noop reuses a live key with the same
    values so the row hash is unchanged.

    Args:
        settings: Dataset settings that define columns and batch composition.
        batch: ``0`` for the full load, ``>= 1`` for an incremental change batch.

    Returns:
        The batch DataFrame and a parallel list of intended row kinds.
    """
    if batch == 0:
        ids = list(range(settings.row_count))
        ops = [RowOp.INSERT] * len(ids)
        frame = _build_rows(
            settings=settings,
            ids=ids,
            versions=dict.fromkeys(ids, 0),
            ops=ops,
        )
        return frame, ops

    live, version, high_water_mark = replay_state(settings, batch)
    inserts, updates, noops = select_batch_ids(
        settings=settings,
        batch=batch,
        live=live,
        high_water_mark=high_water_mark,
    )
    ids = inserts + updates + noops
    ops = [RowOp.INSERT] * len(inserts) + [RowOp.UPDATE] * len(updates) + [RowOp.NOOP] * len(noops)
    versions = {**dict.fromkeys(inserts, batch), **dict.fromkeys(updates, batch)}
    for row_id in noops:
        versions[row_id] = version.get(row_id, 0)
    return _build_rows(settings=settings, ids=ids, versions=versions, ops=ops), ops


def _build_rows(
    settings: MockDatasetSettings,
    ids: list[int],
    versions: dict[int, int],
    ops: list[RowOp],
) -> pd.DataFrame:
    """
    Materialize a DataFrame from ids, versions, and ops.

    Args:
        settings: Dataset settings that define columns.
        ids: Row identities in emission order.
        versions: Last insert/update batch per id.
        ops: Change-tracking operation per emitted row.

    Returns:
        A DataFrame of configured columns plus ``modified_at``. ``op_column``
        is included only when explicitly configured.
    """
    data: dict[str, Any] = {}
    for column in settings.columns:
        data[column.name] = [_cell(settings=settings, column=column, row_id=row_id, version=versions[row_id]) for row_id in ids]
    if settings.op_column is not None:
        data[settings.op_column] = pd.Series([op.value for op in ops], dtype="string")
    data[settings.modified_at_column] = [
        pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=versions[row_id]) + pd.Timedelta(minutes=row_id)
        for row_id in ids
    ]
    frame = pd.DataFrame(data)
    for column in settings.columns:
        if column.null_every:
            mask = pd.Series(ids).mod(column.null_every).eq(0).to_numpy()
            values = frame[column.name].astype("object")
            values[mask] = None
            frame[column.name] = values
    return frame


def _cell(settings: MockDatasetSettings, column: MockColumn, row_id: int, version: int) -> Any:
    """
    Compute one cell value as a pure function of seed, column, id, and version.

    Args:
        settings: Dataset settings containing the determinism seed.
        column: Column definition.
        row_id: Row identity.
        version: Last insert/update batch for this id. ``0`` reproduces the original value.

    Returns:
        A scalar cell value.

    Raises:
        ReadError: If the column kind is unknown.
    """
    if column.kind == ColumnKind.SEQUENCE:
        return row_id
    if column.kind == ColumnKind.CONSTANT:
        return column.value
    if column.kind == ColumnKind.TEXT:
        suffix = f"_v{version}" if version else ""
        return f"{column.prefix}{row_id}{suffix}"
    if column.kind == ColumnKind.BOOL:
        return bool((row_id + version) % 2 == 0)
    if column.kind == ColumnKind.TIMESTAMP:
        return pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=row_id) + pd.Timedelta(hours=version)

    rng = _rng(settings.seed, column.name, row_id, version)
    if column.kind == ColumnKind.RANDOM_INT:
        return int(rng.randrange(column.low, column.high))
    if column.kind == ColumnKind.RANDOM_FLOAT:
        return float(rng.uniform(column.low, column.high))
    raise ReadError(
        message=f"unknown column kind {column.kind!r}",
        code="invalid_settings",
        status_code=400,
        details={"column": column.name},
    )
