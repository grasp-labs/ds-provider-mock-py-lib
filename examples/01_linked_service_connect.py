"""
**File:** ``01_linked_service_connect.py``
**Region:** ``examples/01_linked_service_connect``

Example 01: Connect to the mock backend using a linked service.

This example demonstrates how to:
- Create a mock linked service
- Connect and inspect the backend handle
- Test the connection
"""

from __future__ import annotations

import logging
from uuid import uuid4

from ds_common_logger_py_lib import Logger
from ds_resource_plugin_py_lib.common.resource.errors import ResourceException

from ds_provider_mock_py_lib.linked_service import MockLinkedService, MockLinkedServiceSettings

Logger.configure(level=logging.DEBUG)
logger = Logger.get_logger(__name__)


def main() -> None:
    """Demonstrate mock linked service connection."""
    linked_service = MockLinkedService(
        id=uuid4(),
        name="mock-linked-service",
        version="1.0.0",
        settings=MockLinkedServiceSettings(),
    )

    try:
        linked_service.connect()
        success, message = linked_service.test_connection()
        if success:
            logger.debug("Connection test successful.")
        else:
            raise ResourceException(message=message)
        logger.debug("Backend call count: %s", linked_service.connection.call_count)
    except ResourceException as exc:
        logger.error("Failed to connect to mock backend: %s", exc.message)
        logger.error("Exception: %s", exc.__dict__)
    finally:
        linked_service.close()


if __name__ == "__main__":
    main()
