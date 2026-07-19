"""
Executable Interface
--------------------
Every unit of work submitted to the Execution Engine must implement this
interface.  Modules own business logic.  VaultCore owns execution.

Implementors
------------
  SecureArchiveScanner   (Secure Archive)
  DocumentImporter       (Document Vault)      [future]
  PasswordAuditor        (Password Vault)      [future]
  SecretImporter         (Developer Vault)     [future]
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vaultcore.execution.interfaces.execution_result import ExecutionResult
    from vaultcore.execution.progress.progress_tracker import ProgressTracker
    from vaultcore.execution.cancellation.cancellation_token import CancellationToken


class Executable(ABC):
    """Base contract for all executable units of work."""

    @abstractmethod
    def execute(
        self,
        progress: "ProgressTracker",
        cancellation: "CancellationToken",
    ) -> "ExecutionResult":
        """
        Perform the work.

        Parameters
        ----------
        progress:
            Use this to report incremental progress.
            Do not update UI directly.
        cancellation:
            Check this regularly inside long loops.
            Raise CancelledError when cancellation is requested.

        Returns
        -------
        ExecutionResult
            Populated result object.  Never return None.
        """
        ...
