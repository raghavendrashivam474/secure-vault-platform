"""
ExecutionResult
---------------
Every Executable returns an ExecutionResult.

The Execution Engine attaches this to the Task record and publishes it
via the Event Bus.  Modules never inspect results directly from threads —
they receive results through events.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExecutionResult:
    """Outcome of a completed Executable."""

    success: bool

    # Human-readable summary
    message: str = ""

    # Arbitrary payload — module-specific
    # e.g. SecureArchive returns a list of archived paths
    payload: Any = None

    # Populated on failure
    error: Optional[Exception] = None

    # Statistics the module wants to surface
    stats: dict = field(default_factory=dict)
