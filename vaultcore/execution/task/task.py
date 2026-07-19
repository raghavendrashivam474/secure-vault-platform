"""
Task
----
The platform's canonical record of one unit of work.

Lifecycle
---------
  CREATED  →  QUEUED  →  RUNNING  →  COMPLETED
                                  →  CANCELLED
                                  →  FAILED

Tasks are created by the Execution Engine.
Modules never instantiate Task directly.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional

from vaultcore.execution.interfaces.execution_result import ExecutionResult


class TaskStatus(Enum):
    CREATED   = auto()
    QUEUED    = auto()
    RUNNING   = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    FAILED    = auto()


@dataclass
class Task:
    """Platform record for one unit of work."""

    # Identity
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_name:    str = ""
    source_module: str = ""

    # Scheduling
    priority: int = 5

    # Lifecycle
    status: TaskStatus = TaskStatus.CREATED

    # Timestamps
    created_at:  Optional[datetime] = None
    started_at:  Optional[datetime] = None
    finished_at: Optional[datetime] = None

    # Outcome
    result: Optional[ExecutionResult] = None

    # ---------------------------------------------------------------------------

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def mark_queued(self) -> None:
        self.status = TaskStatus.QUEUED

    def mark_running(self) -> None:
        self.status     = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self, result: ExecutionResult) -> None:
        self.status      = TaskStatus.COMPLETED
        self.finished_at = datetime.utcnow()
        self.result      = result

    def mark_failed(self, error: Exception) -> None:
        self.status      = TaskStatus.FAILED
        self.finished_at = datetime.utcnow()
        self.result      = ExecutionResult(success=False, error=error)

    def mark_cancelled(self) -> None:
        self.status      = TaskStatus.CANCELLED
        self.finished_at = datetime.utcnow()
