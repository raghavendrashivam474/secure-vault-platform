"""
TaskManager
-----------
Owns the queue of pending tasks and their lifecycle transitions.

The Execution Engine calls TaskManager to:
  - Enqueue new tasks
  - Pop the next task for a worker
  - Update task status as execution progresses

The TaskManager does NOT create threads.
Thread management belongs to WorkerManager.
"""

import queue
import threading
from typing import Optional

from vaultcore.execution.task.task import Task, TaskStatus
from vaultcore.execution.task.task_registry import TaskRegistry


class TaskManager:
    """Queue and lifecycle manager for Tasks."""

    def __init__(self) -> None:
        self._queue:    queue.PriorityQueue = queue.PriorityQueue()
        self._registry: TaskRegistry        = TaskRegistry()
        self._lock:     threading.Lock      = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(self, task: Task) -> None:
        """Add a task to the execution queue."""
        task.mark_queued()
        self._registry.register(task)
        # PriorityQueue is a min-heap; lower priority number = higher urgency
        self._queue.put((task.priority, task.execution_id, task))

    def next_task(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Task]:
        """Return the next task for a worker, or None if the queue is empty."""
        try:
            _, _, task = self._queue.get(block=block, timeout=timeout)
            return task
        except queue.Empty:
            return None

    def get_task(self, execution_id: str) -> Optional[Task]:
        """Look up any task by ID regardless of its current status."""
        return self._registry.get(execution_id)

    def all_tasks(self) -> list:
        return self._registry.all()
