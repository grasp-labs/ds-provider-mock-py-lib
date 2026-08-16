"""
**File:** ``read.py``
**Region:** ``ds_provider_mock_py_lib/dataset/engines``

Read engine for paginated mock execution.

This engine is intentionally stateful:
- ``output`` accumulates collected rows page-by-page
- ``checkpoint`` tracks incremental watermark and pagination resume state
- ``metadata`` records batch, page, and op counts

Example:
    >>> from ds_provider_mock_py_lib.dataset.engines.read import ReadEngine
    >>> from ds_provider_mock_py_lib.dataset.settings import MockDatasetSettings
    >>> from ds_provider_mock_py_lib.linked_service import MockBackend, MockLinkedServiceSettings
    >>> engine = ReadEngine(
    ...     connection=MockBackend(MockLinkedServiceSettings()),
    ...     settings=MockDatasetSettings(row_count=2),
    ...     dataset_name="mock-ds",
    ...     provider_type="ds.resource.dataset.mock",
    ... )
    >>> engine.execute(checkpoint={})
    >>> len(engine.output.index)
    2
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pandas as pd
from ds_common_logger_py_lib import Logger
from ds_resource_plugin_py_lib.common.resource.dataset.errors import ReadError
from ds_resource_plugin_py_lib.common.resource.linked_service.errors import ConnectionError

from ...enums import RaiseAs
from ...errors import MockBackendError, resolve_status_code
from ._read_checkpoint import Checkpoint, decode_pagination_cursor, encode_pagination_cursor
from ._read_rows import build_batch_rows

if TYPE_CHECKING:
    from ...linked_service.mock import MockBackend
    from ..settings import MockDatasetSettings

logger = Logger.get_logger(__name__, package=True)


@dataclass(kw_only=True)
class ReadEngine:
    """Execute mock reads including pagination, resume, and failure injection."""

    connection: MockBackend
    settings: MockDatasetSettings
    dataset_name: str
    provider_type: str
    output: pd.DataFrame = field(default_factory=pd.DataFrame, init=False)
    checkpoint: Checkpoint = field(default_factory=Checkpoint, init=False)
    metadata: dict[str, Any] = field(default_factory=dict, init=False)
    _emitted_ops: list[str] = field(default_factory=list, init=False)

    def execute(self, checkpoint: dict[str, Any] | None = None) -> None:
        """
        Execute read flow and update ``output`` / ``checkpoint`` state.

        Args:
            checkpoint: Existing checkpoint state to continue from.

        Raises:
            ReadError: If settings are invalid or a wrapped backend failure occurs.
            ConnectionError: If dataset-level injection is configured as a connection error.
            MockBackendError: If the mock backend raises and the caller must wrap it.
        """
        self.output = pd.DataFrame()
        self.metadata = {}
        self._emitted_ops = []
        try:
            self.checkpoint = Checkpoint.deserialize(checkpoint or {})
        except Exception as exc:
            raise ReadError(
                message=f"Invalid checkpoint: {exc}",
                status_code=400,
                details={"provider": self.provider_type, "dataset": self.dataset_name},
            ) from exc

        self._validate_settings()
        batch, first_page, resumed = self._resolve_start()
        rows, row_ops = build_batch_rows(settings=self.settings, batch=batch)
        page_size = self.settings.page_size or max(len(rows), 1)
        total_pages = max(-(-len(rows) // page_size), 0) if len(rows) else 0

        pages: list[pd.DataFrame] = []
        self.output = pd.DataFrame(columns=list(rows.columns))

        logger.debug(
            "Starting mock read (dataset=%s, batch=%s, first_page=%s, total_pages=%s, resumed=%s).",
            self.dataset_name,
            batch,
            first_page,
            total_pages,
            resumed,
        )

        for page_no in range(first_page, total_pages + 1):
            low = (page_no - 1) * page_size
            high = min(page_no * page_size, len(rows))
            details = {
                "provider": self.provider_type,
                "dataset": self.dataset_name,
                "batch": batch,
                "page": page_no,
                "pages": total_pages,
                "page_size": page_size,
            }
            try:
                self.connection.request(page_no)
                if self.settings.raise_on_page == page_no:
                    self._inject_failure(details)
            except MockBackendError:
                self._save_pagination(batch=batch, page=page_no)
                self._assign_output(pages)
                raise
            except Exception:
                self._save_pagination(batch=batch, page=page_no)
                self._assign_output(pages)
                raise

            if self.settings.page_delay_ms:
                time.sleep(self.settings.page_delay_ms / 1000)

            pages.append(rows.iloc[low:high].copy())
            self._emitted_ops.extend(op.value for op in row_ops[low:high])
            self._assign_output(pages)
            self._save_pagination(batch=batch, page=page_no + 1)

        self._finish_complete(batch=batch, pages=pages, total_pages=total_pages, resumed=resumed)

    def _validate_settings(self) -> None:
        """Raise when settings cannot fulfil a read."""
        settings = self.settings
        if settings.row_count < 0:
            raise ReadError(
                message="row_count must be >= 0",
                code="invalid_settings",
                status_code=400,
                details={"provider": self.provider_type, "row_count": settings.row_count},
            )
        if settings.page_size is not None and settings.page_size < 1:
            raise ReadError(
                message="page_size must be >= 1 when set",
                code="invalid_settings",
                status_code=400,
                details={"provider": self.provider_type, "page_size": settings.page_size},
            )
        column_names = [column.name for column in settings.columns]
        reserved = [settings.modified_at_column]
        if settings.op_column is not None:
            reserved.append(settings.op_column)
        colliding = [name for name in reserved if name in column_names]
        if colliding:
            raise ReadError(
                message="op_column and modified_at_column must not collide with configured columns",
                code="invalid_settings",
                status_code=400,
                details={
                    "provider": self.provider_type,
                    "op_column": settings.op_column,
                    "modified_at_column": settings.modified_at_column,
                    "columns": column_names,
                    "colliding": colliding,
                },
            )
        if len(column_names) != len(set(column_names)):
            raise ReadError(
                message="column names must be unique",
                code="invalid_settings",
                status_code=400,
                details={"provider": self.provider_type, "columns": column_names},
            )

    def _resolve_start(self) -> tuple[int, int, bool]:
        """
        Resolve batch, first page, and whether this call is a resume.

        Returns:
            ``(batch, first_page, resumed)``.

        Raises:
            ReadError: If a stored pagination cursor cannot be decoded.
        """
        pagination_value = self.checkpoint.pagination.value
        if pagination_value:
            try:
                batch, first_page = decode_pagination_cursor(pagination_value)
            except ValueError as exc:
                raise ReadError(
                    message=f"Invalid pagination cursor: {pagination_value!r}",
                    status_code=400,
                    details={"provider": self.provider_type, "dataset": self.dataset_name},
                ) from exc
            return batch, first_page, True

        incremental_value = self.checkpoint.incremental.value
        if incremental_value is not None:
            return int(incremental_value) + 1, 1, False
        return 0, 1, False

    def _save_pagination(self, *, batch: int, page: int) -> None:
        """Persist pagination resume state without advancing the watermark."""
        self.checkpoint.pagination.value = encode_pagination_cursor(batch=batch, page=page)

    def _assign_output(self, pages: list[pd.DataFrame]) -> None:
        """
        Assign concatenated pages to ``output``, including rows already read on failure.

        Args:
            pages: Pages collected so far in this read.
        """
        if pages:
            self.output = pd.concat(pages, ignore_index=True)
            return
        self.output = pd.DataFrame() if self.output is None else self.output

    def _finish_complete(
        self,
        *,
        batch: int,
        pages: list[pd.DataFrame],
        total_pages: int,
        resumed: bool,
    ) -> None:
        """
        Complete a successful read of the configured scope.

        Args:
            batch: Completed batch number written to the incremental watermark.
            pages: Pages collected during this read.
            total_pages: Page count for the current batch.
            resumed: Whether this call continued from a pagination cursor.
        """
        self._assign_output(pages)
        self.checkpoint.pagination.value = None
        self.checkpoint.incremental.value = batch
        self._set_metadata(batch=batch, total_pages=total_pages, resumed=resumed)
        logger.debug(
            "Mock read completed (dataset=%s, batch=%s, rows=%s).",
            self.dataset_name,
            batch,
            len(self.output.index),
        )

    def _set_metadata(self, *, batch: int, total_pages: int, resumed: bool) -> None:
        """
        Populate engine metadata used by ``self.operation.metadata``.

        Args:
            batch: Batch number that was read.
            total_pages: Page count for the current batch.
            resumed: Whether this call continued from a pagination cursor.
        """
        self.metadata = {
            "batch": batch,
            "pages": total_pages,
            "backend_calls": self.connection.call_count,
            "ops": dict(Counter(self._emitted_ops)),
            "resumed": resumed,
        }

    def _inject_failure(self, details: dict[str, Any]) -> None:
        """
        Raise the configured dataset-level contract exception.

        Args:
            details: Page context attached to the raised exception.

        Raises:
            ConnectionError: When ``raise_as`` is ``connection_error``.
            ReadError: When ``raise_as`` is ``read_error``.
        """
        error = self.settings.raise_error
        status_code = resolve_status_code(error.status_code, 500)
        if self.settings.raise_as == RaiseAs.CONNECTION_ERROR:
            raise ConnectionError(
                message=error.message,
                code=error.code,
                status_code=status_code,
                details=details,
            )
        raise ReadError(
            message=error.message,
            code=error.code,
            status_code=status_code,
            details=details,
        )
