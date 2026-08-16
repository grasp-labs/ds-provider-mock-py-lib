"""
**File:** ``test_dataset_unsupported.py``
**Region:** ``tests/dataset/test_dataset_unsupported``

Read-only method tests for MockDataset.
"""

from __future__ import annotations

import pytest
from ds_resource_plugin_py_lib.common.resource.errors import NotSupportedError

from tests.mocks import create_dataset


@pytest.mark.parametrize(
    "method_name",
    ["create", "update", "upsert", "delete", "purge", "rename", "list"],
)
def test_write_and_discovery_methods_are_not_supported(method_name: str) -> None:
    """It raises NotSupportedError for methods the mock does not implement."""
    dataset = create_dataset(row_count=1, connect=False)
    with pytest.raises(NotSupportedError) as exc_info:
        getattr(dataset, method_name)()
    assert method_name in exc_info.value.message
    assert exc_info.value.details["method"] == method_name
