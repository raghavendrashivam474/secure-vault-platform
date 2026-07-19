"""
ExecutionPolicy
---------------
The Decision Engine's output.

Tells the Execution Engine:
  - Whether to run in the background or block
  - What priority to assign
  - Which retry policy to apply
  - Whether verification is required

The Execution Engine consults this before dispatching work.
"""

from dataclasses import dataclass, field
from vaultcore.execution.retry.retry_policy import RetryPolicy


@dataclass
class ExecutionPolicy:
    """How the Execution Engine should handle a specific request."""

    run_in_background:    bool        = True
    priority:             int         = 5
    retry_policy:         RetryPolicy = field(default_factory=RetryPolicy)
    requires_verification: bool       = False
    timeout_seconds:      float       = 0.0   # 0 = no timeout
