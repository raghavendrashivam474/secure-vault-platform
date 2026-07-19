"""
Execution Events
----------------
The canonical set of events published by the Execution Engine.

Consumers
---------
  - Progress UI widgets
  - Activity Monitor panel
  - Notification system
  - Application log

Publishers
----------
  - Worker  (via EventDispatcher)

Every event carries enough information to render UI without
querying the Task directly.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from vaultcore.execution.task.task import Task
    from vaultcore.execution.interfaces.execution_result import ExecutionResult
    from vaultcore.execution.progress.progress_model import ProgressModel


@dataclass
class ExecutionStartedEvent:
    task:       "Task"
    timestamp:  datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProgressUpdatedEvent:
    execution_id: str
    task_name:    str
    progress:     "ProgressModel"
    timestamp:    datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionCompletedEvent:
    task:      "Task"
    result:    "ExecutionResult"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionFailedEvent:
    task:      "Task"
    error:     Exception
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionCancelledEvent:
    task:      "Task"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionWarningEvent:
    execution_id: str
    message:      str
    timestamp:    datetime = field(default_factory=datetime.utcnow)
