"""
**File:** ``enums.py``
**Region:** ``ds_provider_mock_py_lib/enums``

Constants for the mock provider.

Example:
    >>> ResourceType.LINKED_SERVICE
    'ds.resource.linked-service.mock'
    >>> ResourceType.DATASET
    'ds.resource.dataset.mock'
    >>> ConnectBehaviour.OK
    'ok'
"""

from enum import StrEnum


class ResourceType(StrEnum):
    """Resource type identifiers for the mock provider."""

    LINKED_SERVICE = "ds.resource.linked-service.mock"
    DATASET = "ds.resource.dataset.mock"


class ConnectBehaviour(StrEnum):
    """What ``connect()`` does. Values are lowercase per the linked-service contract."""

    OK = "ok"
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"


class ColumnKind(StrEnum):
    """Synthetic column value generators used by ``MockDataset``."""

    SEQUENCE = "sequence"
    CONSTANT = "constant"
    TEXT = "text"
    RANDOM_INT = "random_int"
    RANDOM_FLOAT = "random_float"
    BOOL = "bool"
    TIMESTAMP = "timestamp"
    ENUM = "enum"


class RowOp(StrEnum):
    """
    Intended row kind for incremental generation and operation metadata.

    These are not gold merge opcodes. Gold decides from primary key and row
    hash:

    - ``insert``: new unique primary key
    - ``update``: existing primary key, changed column values (hash changes)
    - ``noop``: existing primary key, identical row (same hash)
    """

    INSERT = "insert"
    UPDATE = "update"
    NOOP = "noop"


class RaiseAs(StrEnum):
    """Which contract exception a dataset-level injected failure raises."""

    READ_ERROR = "read_error"
    CONNECTION_ERROR = "connection_error"
