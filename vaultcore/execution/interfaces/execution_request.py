"""
ExecutionRequest
----------------
Modules construct an ExecutionRequest and hand it to the Execution Engine.

The request carries:
  - What to execute  (an Executable)
  - Hints for the Decision Engine  (priority, context)
  - Caller identity  (which module is submitting)

The Execution Engine uses the ExecutionPolicy produced by the Decision Engine
to determine how the request is fulfilled.
"""

from dataclasses import dataclass, field
from typing import Optional
from vaultcore.execution.interfaces.executable import Executable


@dataclass
class ExecutionRequest:
    """Describes a unit of work to be executed by VaultCore."""

    # The callable unit of work
    executable: Executable

    # Human-readable label (appears in progress UI and logs)
    task_name: str

    # Which module is submitting — e.g. "secure_archive", "password_vault"
    source_module: str

    # Relative priority hint — Decision Engine may override
    priority: int = 5   # 1 = highest, 10 = lowest

    # Free-form context the Decision Engine can inspect
    context: dict = field(default_factory=dict)

    # Optional caller-supplied correlation id
    correlation_id: Optional[str] = None
