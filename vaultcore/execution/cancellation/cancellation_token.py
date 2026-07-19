"""
CancellationToken
-----------------
Cooperative cancellation signal passed to every Executable.

Pattern
-------
  def execute(self, progress, cancellation):
      for item in large_collection:
          if cancellation.is_cancelled:
              return ExecutionResult(success=False, message='Cancelled')
          # ... do work ...

The WorkerManager calls token.cancel() in response to a UI cancel action.
Executables are never killed forcefully.
"""

import threading


class CancellationToken:
    """Thread-safe cooperative cancellation signal."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        """Signal that execution should stop at the next checkpoint."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()
