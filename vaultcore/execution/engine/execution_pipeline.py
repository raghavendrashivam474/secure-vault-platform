"""
ExecutionPipeline
-----------------
Runs every ExecutionRequest through the canonical lifecycle.

  Validate → Analyze → Decision → Prepare → Execute → Verify → Cleanup → Complete

Sprint 17 — Validate and Decision are active.
Remaining stages are stubs that pass through transparently.

Adding a stage in a future sprint requires changing only this file.
"""

from vaultcore.execution.interfaces.execution_request import ExecutionRequest
from vaultcore.execution.decision.decision_engine import DecisionEngine
from vaultcore.execution.decision.execution_policy import ExecutionPolicy


class ExecutionPipeline:
    """Pre-execution pipeline that validates and enriches a request."""

    def __init__(self, decision_engine: DecisionEngine) -> None:
        self._decision_engine = decision_engine

    def process(self, request: ExecutionRequest) -> ExecutionPolicy:
        """
        Run the request through all pipeline stages.

        Returns the ExecutionPolicy the Execution Engine should apply.
        """
        self._validate(request)
        policy = self._decide(request)
        self._prepare(request, policy)
        return policy

    # ------------------------------------------------------------------

    def _validate(self, request: ExecutionRequest) -> None:
        if not request.executable:
            raise ValueError("ExecutionRequest must carry an Executable.")
        if not request.task_name:
            raise ValueError("ExecutionRequest must have a task_name.")

    def _decide(self, request: ExecutionRequest) -> ExecutionPolicy:
        return self._decision_engine.decide(request)

    def _prepare(self, request: ExecutionRequest, policy: ExecutionPolicy) -> None:
        # Sprint 17 — nothing to prepare
        pass
