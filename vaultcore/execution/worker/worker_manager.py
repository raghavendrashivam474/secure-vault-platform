"""
WorkerManager
-------------
Owns the lifecycle of all Worker threads.

Sprint 17 — starts exactly one Worker.
Future sprints increase the pool size via configuration only.
No module code changes.
"""

from vaultcore.execution.worker.worker_pool import WorkerPool
from vaultcore.execution.task.task_manager import TaskManager
from vaultcore.execution.events.event_dispatcher import EventDispatcher


class WorkerManager:
    """Manages creation, startup, and shutdown of Worker threads."""

    def __init__(
        self,
        task_manager: TaskManager,
        dispatcher:   EventDispatcher,
        pool_size:    int = 1,        # Sprint 17 default
    ) -> None:
        self._pool = WorkerPool(
            task_manager = task_manager,
            dispatcher   = dispatcher,
            size         = pool_size,
        )

    def start(self) -> None:
        """Start all workers.  Called once at application startup."""
        self._pool.start_all()

    def stop(self) -> None:
        """Gracefully stop all workers.  Called at application shutdown."""
        self._pool.stop_all()
