"""
RetryPolicy
-----------
Describes how many times an Executable should be retried on failure.

Sprint 17 — the Execution Engine does not yet apply retry logic.
This class is scaffolded so the architecture is complete.

Future integration
------------------
  The Decision Engine will attach a RetryPolicy to an ExecutionPolicy.
  The Execution Engine will consult it before marking a task FAILED.
"""

from dataclasses import dataclass


@dataclass
class RetryPolicy:
    """Configures automatic retry behaviour for a Task."""

    max_attempts:        int   = 1        # 1 = no retry
    delay_seconds:       float = 2.0
    backoff_multiplier:  float = 1.0      # 2.0 = exponential backoff

    @property
    def will_retry(self) -> bool:
        return self.max_attempts > 1
