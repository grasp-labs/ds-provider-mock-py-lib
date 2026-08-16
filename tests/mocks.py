"""
**File:** ``mocks.py``
**Region:** ``tests/mocks``

Shared factories for mock provider tests.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from ds_provider_mock_py_lib.dataset import MockDataset, MockDatasetSettings
from ds_provider_mock_py_lib.linked_service import MockLinkedService, MockLinkedServiceSettings


def create_linked_service(**settings_kwargs: Any) -> MockLinkedService:
    """
    Create a mock linked service for tests.

    Args:
        settings_kwargs: Fields forwarded to ``MockLinkedServiceSettings``.

    Returns:
        An unconnected ``MockLinkedService``.
    """
    return MockLinkedService(
        id=uuid4(),
        name="test-linked-service",
        version="1.0.0",
        settings=MockLinkedServiceSettings(**settings_kwargs),
    )


def create_dataset(
    linked_service: MockLinkedService | None = None,
    connect: bool = True,
    **settings_kwargs: Any,
) -> MockDataset:
    """
    Create a mock dataset for tests.

    Args:
        linked_service: Optional linked service. Created when omitted.
        connect: When ``True``, connect the linked service before returning.
        settings_kwargs: Fields forwarded to ``MockDatasetSettings``.

    Returns:
        A ``MockDataset`` ready for ``read()``.
    """
    if linked_service is None:
        linked_service = create_linked_service()
    if connect:
        linked_service.connect()
    return MockDataset(
        id=uuid4(),
        name="test-dataset",
        version="1.0.0",
        linked_service=linked_service,
        settings=MockDatasetSettings(**settings_kwargs),
    )
