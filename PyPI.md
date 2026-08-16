# ds-provider-mock-py-lib

Mock provider for DS pipeline e2e testing. Read-only, deterministic,
CDC-style change batches that bronze can load as a real `ds.providers`
plugin.

## Installation

```bash
pip install ds-provider-mock-py-lib
```

Or using uv:

```bash
uv pip install ds-provider-mock-py-lib
```

## Quick Start

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
    settings=MockDatasetSettings(row_count=25),
)

linked_service.connect()
dataset.read()
assert len(dataset.output.index) == 25
linked_service.close()
```

## Features

- Deterministic snapshot and incremental CDC batches
- Scriptable connect, auth, and per-request failures
- Xledger-style checkpoint (`incremental` + `pagination`)
- Pagination resume after injected read failures

## Usage

Full load then one incremental change batch:

```python
dataset.settings.incremental_insert_count = 5
dataset.settings.incremental_update_count = 3
dataset.settings.incremental_noop_count = 2

dataset.checkpoint = {}
dataset.read()  # batch 0, all inserts
state = dataset.checkpoint

dataset.checkpoint = state
dataset.read()  # batch 1: new keys, changed hashes, identical re-delivery
```

## Requirements

- Python 3.11 or higher
- `ds-resource-plugin-py-lib`
- `pandas`

## Documentation

Full documentation is available at:

- [GitHub Repository](https://github.com/grasp-labs/ds-provider-mock-py-lib)
- [Documentation Site](https://grasp-labs.github.io/ds-provider-mock-py-lib/)

## Development

```bash
git clone https://github.com/grasp-labs/ds-provider-mock-py-lib.git
cd ds-provider-mock-py-lib
uv sync --all-extras --dev
make test
```

See the [README](https://github.com/grasp-labs/ds-provider-mock-py-lib#readme)
for more information.

## License

This package is licensed under the Apache License 2.0.
See the [LICENSE-APACHE](https://github.com/grasp-labs/ds-provider-mock-py-lib/blob/main/LICENSE-APACHE)
file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/grasp-labs/ds-provider-mock-py-lib/issues)
- **Releases**: [GitHub Releases](https://github.com/grasp-labs/ds-provider-mock-py-lib/releases)
