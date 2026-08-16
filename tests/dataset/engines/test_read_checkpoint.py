"""
**File:** ``test_read_checkpoint.py``
**Region:** ``tests/dataset/engines/test_read_checkpoint``

Checkpoint encode/decode tests.
"""

from __future__ import annotations

import pytest

from ds_provider_mock_py_lib.dataset.engines._read_checkpoint import (
    Checkpoint,
    decode_pagination_cursor,
    encode_pagination_cursor,
)


def test_empty_checkpoint_deserializes_to_defaults() -> None:
    """An empty dict is a full load: no watermark and no pagination."""
    checkpoint = Checkpoint.deserialize({})
    assert checkpoint.incremental.value is None
    assert checkpoint.pagination.value is None


def test_encode_and_decode_pagination_cursor() -> None:
    """It round-trips batch and page through the opaque cursor."""
    cursor = encode_pagination_cursor(batch=4, page=2)
    assert decode_pagination_cursor(cursor) == (4, 2)


def test_decode_pagination_cursor_rejects_malformed_value() -> None:
    """It raises ValueError for a cursor that is not batch:page."""
    with pytest.raises(ValueError, match="Invalid pagination cursor"):
        decode_pagination_cursor("only-one-part")


def test_checkpoint_serialize_shape_matches_xledger() -> None:
    """It serializes incremental and pagination objects."""
    checkpoint = Checkpoint.deserialize({"incremental": {"value": 0}, "pagination": {"value": "1:2"}})
    payload = checkpoint.serialize()
    assert payload["incremental"]["value"] == 0
    assert payload["pagination"]["value"] == "1:2"
