# ds-provider-mock-py-lib

![Python Versions](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue)
[![PyPI version](https://badge.fury.io/py/ds-provider-mock-py-lib.svg?kill_cache=1)](https://badge.fury.io/py/ds-provider-mock-py-lib)
[![Build Status](https://github.com/grasp-labs/ds-provider-mock-py-lib/actions/workflows/build.yaml/badge.svg)](https://github.com/grasp-labs/ds-provider-mock-py-lib/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/grasp-labs/ds-provider-mock-py-lib/graph/badge.svg?token=EO3YCNCZFS)](https://codecov.io/gh/grasp-labs/ds-provider-mock-py-lib)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Mock provider for DS pipeline e2e testing. It is a real `ds.providers`
plugin: bronze can load it, read deterministic rows, and script connect,
read, and checkpoint outcomes without a live third-party backend.

## Quick Start

```shell
uv sync --all-extras --dev
uv run pre-commit install
make test
```

```python
from uuid import uuid4

from ds_provider_mock_py_lib import (
    MockDataset,
    MockDatasetSettings,
    MockLinkedService,
    MockLinkedServiceSettings,
)

linked_service = MockLinkedService(
    id=uuid4(),
    name="mock-ls",
    version="1.0.0",
    settings=MockLinkedServiceSettings(),
)
dataset = MockDataset(
    id=uuid4(),
    name="mock-ds",
    version="1.0.0",
    linked_service=linked_service,
    settings=MockDatasetSettings(row_count=25, page_size=10),
)

linked_service.connect()
dataset.read()
print(len(dataset.output.index), dataset.checkpoint)
linked_service.close()
```

## What it is for

Use this provider in pipeline e2e tests when a live source cannot be
scripted. Settings control:

- Snapshot size and synthetic columns
- Incremental CDC mix: new keys (`insert`), changed values (`update`),
  identical re-delivery (`noop`)
- Pagination and mid-read failure injection
- Connect, auth, and per-request backend failures

Gold merge should use primary key plus row hash, not a source `_op`
column (that column is off by default so it cannot change a noop hash).
Inserts are new keys. Updates reuse a key with changed values. Noops
reuse a key with an identical row. Values are a pure function of
`(seed, id, version, batch)`.

## Checkpoint

Checkpoint shape follows the Xledger provider: incremental watermark plus
optional pagination cursor.

- Empty / missing watermark
  - Checkpoint:
    `{"incremental": {"value": null}, "pagination": {"value": null}}`
  - Read behaviour: Full load, batch `0`
- Successful snapshot
  - Checkpoint:
    `{"incremental": {"value": 0}, "pagination": {"value": null}}`
  - Read behaviour: Next incremental batch
- Failed mid-batch
  - Checkpoint:
    `{"incremental": {"value": 0}, "pagination": {"value": "1:2"}}`
  - Read behaviour: Resume batch `1` at page `2`

The incremental watermark advances only after a fully successful read.
Pagination is updated as pages complete and is cleared when the batch
finishes. The caller persists `dataset.checkpoint`; the provider only
reads and updates it.

## Field classification

### Linked service

- **Exposed:** `id`, `name`, `description`, `version`, `settings.*`
- **Internal:** `_connection`, `_connect_attempts`

### Dataset

- **Exposed:** `id`, `name`, `description`, `version`, `settings.*`,
  `linked_service`, `serializer`, `deserializer`
- **Internal / runtime (base class):** `input`, `output`, `operation`,
  `checkpoint`

Write methods (`create`, `update`, `upsert`, `delete`, `purge`,
`rename`, `list`) raise `NotSupportedError`. The mock is read-only.

## Development

```shell
make help
make lint
make format
make type-check
make test
make test-cov
```

Examples:

- `examples/01_linked_service_connect.py`
- `examples/02_dataset_read.py`
- `examples/03_dataset_incremental.py`
- `examples/04_dataset_failure_resume.py`
- `examples/05_linked_service_failures.py`
- `examples/06_dataset_raise_scenarios.py`
- `examples/07_dataset_backend_failures.py`

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Make (for development commands)

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [PyPI.md](PyPI.md)
- [README.md](README.md)

## License

This package is licensed under the Apache License 2.0.
See [LICENSE-APACHE](LICENSE-APACHE) for details.
