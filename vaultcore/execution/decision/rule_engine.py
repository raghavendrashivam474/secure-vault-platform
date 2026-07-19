"""
RuleEngine
----------
Deterministic rule evaluation for Sprint 17.

Rules are evaluated in order.  The first matching rule wins.

Sprint 17 ships with one rule:
  - Everything runs in the background at default priority.

Future rules might include:
  - Small payloads run immediately (no background thread)
  - Password audits run at lower priority
  - Restoration tasks run at highest priority
"""

from vaultcore.execution.interfaces.execution_request import ExecutionRequest
from vaultcore.execution.decision.execution_policy import ExecutionPolicy


class RuleEngine:
    """Evaluates deterministic rules to produce an ExecutionPolicy."""

    def evaluate(self, request: ExecutionRequest) -> ExecutionPolicy:
        """
        Evaluate rules against the request and return an ExecutionPolicy.

        Sprint 17 — single catch-all rule.
        """
        # Rule 1 — default: everything runs in the background
        return ExecutionPolicy(
            run_in_background = True,
            priority          = request.priority,
        )
