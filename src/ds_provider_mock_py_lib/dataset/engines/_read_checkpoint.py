"""
**File:** ``_read_checkpoint.py``
**Region:** ``ds_provider_mock_py_lib/dataset/engines``

Checkpoint models for mock read continuation.

The shape matches Xledger: incremental watermark plus optional pagination
cursor. For the mock provider:

- ``incremental.value`` is the last *completed* batch number (``0`` after a
  successful full load).
- ``pagination.value`` is an opaque ``"{batch}:{page}"`` cursor used to resume
  an unfinished paginated traversal.

Example:
    >>> from ds_provider_mock_py_lib.dataset.engines._read_checkpoint import Checkpoint
    >>> checkpoint = Checkpoint.deserialize({})
    >>> checkpoint.incremental.value is None
    True
    >>> checkpoint.pagination.value is None
    True
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ds_common_serde_py_lib.serializable import Serializable


@dataclass(kw_only=True)
class CheckpointIncremental(Serializable):
    """Store the persisted incremental watermark.

    Attributes:
        value: Last completed batch number, or ``None`` when no snapshot exists.
    """

    value: Any = None


@dataclass(kw_only=True)
class CheckpointPagination(Serializable):
    """Store the persisted pagination continuation token.

    Attributes:
        value: Cursor used to resume an unfinished paginated traversal.
    """

    value: str | None = None


@dataclass(kw_only=True)
class Checkpoint(Serializable):
    """Store checkpoint state for resumable reads.

    Attributes:
        incremental: Persisted incremental watermark state.
        pagination: Persisted pagination continuation state.
    """

    incremental: CheckpointIncremental = field(default_factory=CheckpointIncremental)
    pagination: CheckpointPagination = field(default_factory=CheckpointPagination)


def encode_pagination_cursor(*, batch: int, page: int) -> str:
    """
    Encode a pagination cursor for the current batch and page.

    Args:
        batch: Batch currently being read.
        page: 1-based page to resume from.

    Returns:
        Opaque ``"{batch}:{page}"`` cursor string.
    """
    return f"{batch}:{page}"


def decode_pagination_cursor(value: str) -> tuple[int, int]:
    """
    Decode a pagination cursor into batch and page.

    Args:
        value: Cursor previously produced by ``encode_pagination_cursor``.

    Returns:
        Tuple of ``(batch, page)``.

    Raises:
        ValueError: If the cursor is not a valid ``batch:page`` pair.
    """
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid pagination cursor: {value!r}")
    return int(parts[0]), int(parts[1])
