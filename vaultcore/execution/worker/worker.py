"""
Worker
------
A single background thread that processes Tasks one at a time.

Sprint 17 — one worker is sufficient.
The WorkerManager adds more workers without changing this class.

The Worker:
  1. Pulls the next Task from TaskManager
  2. Marks it RUNNING
  3. Calls executable.execute(progress, cancellation)
  4. Publishes events via EventDispatcher
  5. Marks the Task COMPLETED / FAILED / CANCELLED
"""

import threading
from datetime import datetime

from vaultcore.execution.task.task import Task
from vaultcore.execution.task.task_manager import TaskManager
from vaultcore.execution.progress.progress_tracker import ProgressTracker
from vaultcore.execution.cancellation.cancellation_token import CancellationToken
from vaultcore.execution.events.event_dispatcher import EventDispatcher
from vaultcore.execution.events.execution_events import (
    ExecutionStartedEvent,
    ExecutionCompletedEvent,
    ExecutionFailedEvent,
    ExecutionCancelledEvent,
)


class Worker(threading.Thread):
    """Background thread that processes Tasks."""

    def __init__(
        self,
        worker_id:   int,
        task_manager: TaskManager,
        dispatcher:   EventDispatcher,
    ) -> None:
        super().__init__(daemon=True, name=f"VaultWorker-{worker_id}")
        self._id           = worker_id
        self._task_manager = task_manager
        self._dispatcher   = dispatcher
        self._stop_event   = threading.Event()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Signal the worker to stop after finishing its current task."""
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Thread entry
    # ------------------------------------------------------------------

    def run(self) -> None:
        while not self._stop_event.is_set():
            task = self._task_manager.next_task(block=True, timeout=1.0)
            if task is None:
                continue
            self._process(task)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _process(self, task: Task) -> None:
        cancellation = CancellationToken()
        progress     = ProgressTracker(
            task_name    = task.task_name,
            dispatcher   = self._dispatcher,
            execution_id = task.execution_id,
        )

        task.mark_running()
        self._dispatcher.dispatch(ExecutionStartedEvent(task=task))

        try:
            result = task.result  # populated below
            result = task.executable.execute(          # type: ignore[attr-defined]
                progress     = progress,
                cancellation = cancellation,
            )
            if cancellation.is_cancelled:
                task.mark_cancelled()
                self._dispatcher.dispatch(ExecutionCancelledEvent(task=task))
            else:
                task.mark_completed(result)
                self._dispatcher.dispatch(ExecutionCompletedEvent(task=task, result=result))

        except Exception as exc:                       # noqa: BLE001
            task.mark_failed(exc)
            self._dispatcher.dispatch(ExecutionFailedEvent(task=task, error=exc))
