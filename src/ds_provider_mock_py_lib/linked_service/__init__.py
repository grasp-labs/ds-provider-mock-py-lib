"""
**File:** ``__init__.py``
**Region:** ``ds_provider_mock_py_lib/linked_service``

Mock Linked Service

This module implements an in-memory linked service for e2e testing.

Example:
    >>> from uuid import uuid4
    >>> from ds_provider_mock_py_lib.linked_service import MockLinkedService, MockLinkedServiceSettings
    >>> linked_service = MockLinkedService(
    ...     id=uuid4(),
    ...     name="mock-connection",
    ...     version="1.0.0",
    ...     settings=MockLinkedServiceSettings(),
    ... )
    >>> linked_service.connect()
"""

from .mock import MockBackend, MockLinkedService, MockLinkedServiceSettings

__all__ = [
    "MockBackend",
    "MockLinkedService",
    "MockLinkedServiceSettings",
]
