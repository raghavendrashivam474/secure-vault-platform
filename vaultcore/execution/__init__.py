"""
VaultCore Execution & Intelligence Foundation
---------------------------------------------
Public surface of the execution package.

Modules import from here only:

    from vaultcore.execution import ExecutionEngine, ExecutionRequest, Executable

Everything else is internal to VaultCore.
"""

from vaultcore.execution.engine.execution_engine       import ExecutionEngine
from vaultcore.execution.interfaces.executable         import Executable
from vaultcore.execution.interfaces.execution_request  import ExecutionRequest
from vaultcore.execution.interfaces.execution_result   import ExecutionResult
from vaultcore.execution.events.execution_events       import (
    ExecutionStartedEvent,
    ProgressUpdatedEvent,
    ExecutionCompletedEvent,
    ExecutionFailedEvent,
    ExecutionCancelledEvent,
    ExecutionWarningEvent,
)

__all__ = [
    "ExecutionEngine",
    "Executable",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStartedEvent",
    "ProgressUpdatedEvent",
    "ExecutionCompletedEvent",
    "ExecutionFailedEvent",
    "ExecutionCancelledEvent",
    "ExecutionWarningEvent",
]
