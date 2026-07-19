"""
TaskRegistry
------------
In-memory store of all Task records created during this session.

Consulted by:
  - Activity Monitor UI
  - Event consumers that need task metadata
  - TaskManager lookups
"""

import threading
from typing import Dict, List, Optional

from vaultcore.execution.task.task import Task


class TaskRegistry:
    """Thread-safe in-memory registry of all Tasks."""

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._lock:  threading.Lock  = threading.Lock()

    def register(self, task: Task) -> None:
        with self._lock:
            self._tasks[task.execution_id] = task

    def get(self, execution_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(execution_id)

    def all(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())
