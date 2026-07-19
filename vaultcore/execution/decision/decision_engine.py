"""
DecisionEngine
--------------
Facade over the rule evaluation pipeline.

Sprint 17 delegates entirely to RuleEngine.

Future architecture:

  RuleEngine
     ↓
  Heuristics
     ↓
  Learning
     ↓
  AI Assistance

Only DecisionEngine needs to change as the pipeline grows.
Modules are unaffected.
"""

from vaultcore.execution.interfaces.execution_request import ExecutionRequest
from vaultcore.execution.decision.execution_policy import ExecutionPolicy
from vaultcore.execution.decision.rule_engine import RuleEngine


class DecisionEngine:
    """Determines how a request should be executed."""

    def __init__(self) -> None:
        self._rule_engine = RuleEngine()

    def decide(self, request: ExecutionRequest) -> ExecutionPolicy:
        """Return an ExecutionPolicy for the given request."""
        return self._rule_engine.evaluate(request)
