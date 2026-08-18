"""
**File:** ``settings.py``
**Region:** ``ds_provider_mock_py_lib/dataset``

Dataset settings for the mock provider.

Example:
    >>> from ds_provider_mock_py_lib.dataset.settings import MockColumn, MockDatasetSettings
    >>> from ds_provider_mock_py_lib.enums import ColumnKind
    >>> settings = MockDatasetSettings(
    ...     columns=[
    ...         MockColumn(name="id", kind=ColumnKind.SEQUENCE),
    ...         MockColumn(name="status", kind=ColumnKind.ENUM, value=["active", "deactive"]),
    ...     ],
    ...     row_count=10,
    ... )
    >>> settings.row_count
    10
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ds_common_serde_py_lib import Serializable
from ds_resource_plugin_py_lib.common.resource.dataset import DatasetSettings

from ..enums import ColumnKind, RaiseAs
from ..models import MockError


@dataclass(kw_only=True)
class MockColumn(Serializable):
    """One synthetic column in a mock dataset."""

    name: str
    """Column name emitted in ``self.output``."""

    kind: ColumnKind = ColumnKind.TEXT
    """Value generator used for this column."""

    value: Any = None
    """
    Payload for ``constant`` and ``enum``.

    A scalar is emitted on every row when ``kind`` is ``constant``. A
    non-empty list is sampled when ``kind`` is ``enum``.
    """

    prefix: str = ""
    """Prefix used when ``kind`` is ``text``."""

    low: int = 0
    """Inclusive lower bound for random numeric kinds."""

    high: int = 1000
    """Exclusive upper bound for random numeric kinds."""

    null_every: int | None = None
    """When set, every Nth id is ``None`` (stable across batches)."""


def default_columns() -> list[MockColumn]:
    """
    Return the default mock column set.

    Returns:
        A sequence column named ``id`` and a text column named ``name``.
    """
    return [
        MockColumn(name="id", kind=ColumnKind.SEQUENCE),
        MockColumn(name="name", kind=ColumnKind.TEXT, prefix="row_"),
    ]


@dataclass(kw_only=True)
class MockDatasetSettings(DatasetSettings):
    """Settings that define mock read scope and injected failure behaviour."""

    columns: list[MockColumn] = field(default_factory=default_columns)
    """Synthetic columns included in every emitted row."""

    row_count: int = 100
    """Rows in the full load (batch 0, all inserts)."""

    incremental_insert_count: int = 0
    """New unique primary keys delivered in each incremental batch."""

    incremental_update_count: int = 0
    """Existing primary keys re-delivered with changed column values (row hash changes)."""

    incremental_noop_count: int = 0
    """Existing primary keys re-delivered with an identical row (same hash)."""

    page_size: int | None = None
    """Page size. ``None`` emits the whole batch in one page."""

    seed: int = 42
    """Determinism seed for id selection and random cell values."""

    page_delay_ms: int = 0
    """Artificial delay applied after each successful page."""

    op_column: str | None = None
    """
    Optional label column for intended row kind.

    Gold merge uses primary key plus row hash, not this column. Leave unset
    so the label cannot change the hash of a noop row. Counts are always in
    ``operation.metadata["ops"]``.
    """

    modified_at_column: str = "_modified_at"
    """Column that stores the deterministic modified-at timestamp."""

    raise_on_page: int | None = None
    """1-based page number within the current batch that should fail. ``None`` disables."""

    raise_as: RaiseAs = RaiseAs.READ_ERROR
    """Contract exception class used when ``raise_on_page`` matches."""

    raise_error: MockError = field(
        default_factory=lambda: MockError(
            message="mock read failure",
            code="mock_read_failure",
            status_code=500,
        )
    )
    """Error spec used when ``raise_on_page`` matches."""
