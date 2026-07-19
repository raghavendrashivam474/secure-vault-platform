"""
ExecutionEngine
---------------
The single public entry point for all long-running work inside VaultCore.

Modules call:
    engine.submit(ExecutionRequest(...))

They receive a Task back so they can observe its lifecycle via the Event Bus.

Internal flow
-------------
  1. ExecutionPipeline validates and produces an ExecutionPolicy
  2. ExecutionEngine creates a Task
  3. TaskManager enqueues the Task
  4. A Worker picks it up, calls executable.execute(), publishes events
  5. Module receives events via its subscribed handlers

Nothing in this class references Secure Archive or any other module.
"""

from datetime import datetime
from typing import Optional

from vaultcore.execution.interfaces.execution_request import ExecutionRequest
from vaultcore.execution.task.task import Task
from vaultcore.execution.task.task_manager import TaskManager
from vaultcore.execution.engine.execution_pipeline import ExecutionPipeline
from vaultcore.execution.decision.decision_engine import DecisionEngine
from vaultcore.execution.worker.worker_manager import WorkerManager
from vaultcore.execution.events.event_dispatcher import EventDispatcher


class ExecutionEngine:
    """
    Top-level coordinator for VaultCore execution.

    Instantiate once at application startup and share via dependency injection.
    """

    def __init__(self) -> None:
        self._dispatcher  = EventDispatcher()
        self._task_manager = TaskManager()
        self._pipeline    = ExecutionPipeline(DecisionEngine())
        self._worker_manager = WorkerManager(
            task_manager = self._task_manager,
            dispatcher   = self._dispatcher,
            pool_size    = 1,              # Sprint 17: single worker
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the execution framework.  Call once at app startup."""
        self._worker_manager.start()

    def stop(self) -> None:
        """Gracefully stop all workers.  Call at app shutdown."""
        self._worker_manager.stop()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, request: ExecutionRequest) -> Task:
        """
        Submit work to the execution framework.

        Parameters
        ----------
        request : ExecutionRequest
            Describes what to execute and execution hints.

        Returns
        -------
        Task
            The platform record.  Subscribe to events to receive results.
        """
        policy = self._pipeline.process(request)

        task = Task(
            task_name     = request.task_name,
            source_module = request.source_module,
            priority      = policy.priority,
        )

        # Attach the executable so the Worker can call it
        task.executable = request.executable          # type: ignore[attr-defined]
        task.created_at = datetime.utcnow()

        self._task_manager.enqueue(task)
        return task

    @property
    def dispatcher(self) -> EventDispatcher:
        """Expose the EventDispatcher so modules can subscribe to events."""
        return self._dispatcher
