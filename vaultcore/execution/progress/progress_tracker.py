"""
ProgressTracker
---------------
Executables call ProgressTracker to report incremental progress.

ProgressTracker converts those calls into ProgressUpdatedEvents and
publishes them via the EventDispatcher.

This is the ONLY way progress reaches the UI.
Executables must not update UI widgets directly.
"""

import time
from typing import Optional

from vaultcore.execution.progress.progress_model import ProgressModel
from vaultcore.execution.events.execution_events import ProgressUpdatedEvent


class ProgressTracker:
    """Translates executable progress calls into platform events."""

    def __init__(
        self,
        task_name:    str,
        dispatcher,                   # EventDispatcher — imported lazily to avoid cycles
        execution_id: str,
    ) -> None:
        self._task_name    = task_name
        self._dispatcher   = dispatcher
        self._execution_id = execution_id
        self._started_at   = time.monotonic()
        self._model        = ProgressModel()

    # ------------------------------------------------------------------
    # Public API — called by Executable implementations
    # ------------------------------------------------------------------

    def begin_step(self, step_name: str, total_items: int = 0) -> None:
        self._model.current_step  = step_name
        self._model.items_total   = total_items
        self._model.items_processed = 0
        self._publish()

    def advance(self, item: str = "", increment: int = 1) -> None:
        self._model.current_item     = item
        self._model.items_processed += increment
        self._model.percentage = (
            (self._model.items_processed / self._model.items_total * 100)
            if self._model.items_total > 0 else 0.0
        )
        self._model.elapsed_seconds = time.monotonic() - self._started_at
        self._publish()

    def set_message(self, message: str) -> None:
        self._model.status_message = message
        self._publish()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _publish(self) -> None:
        import copy
        self._dispatcher.dispatch(
            ProgressUpdatedEvent(
                execution_id = self._execution_id,
                task_name    = self._task_name,
                progress     = copy.copy(self._model),
            )
        )
