"""
modules/secure_archive/core/scan_executable.py

Wraps InputScanner as a VaultCore Executable.

Sprint 17 — this is the ONLY new file inside Secure Archive.
InputScanner is not modified. Business logic is untouched.
Execution infrastructure belongs to VaultCore.
"""

from pathlib import Path

from vaultcore.execution.interfaces.executable import Executable
from vaultcore.execution.interfaces.execution_result import ExecutionResult
from vaultcore.execution.progress.progress_tracker import ProgressTracker
from vaultcore.execution.cancellation.cancellation_token import CancellationToken

from modules.secure_archive.core.input_scanner import InputScanner


class ScanExecutable(Executable):
    """
    Runs InputScanner on a VaultCore background worker thread.

    The dashboard submits this via ExecutionEngine.submit().
    The result (ScanResult) is delivered through ExecutionCompletedEvent.
    The UI never blocks.
    """

    def __init__(self, source_path: Path) -> None:
        self._source_path = source_path

    def execute(
        self,
        progress: ProgressTracker,
        cancellation: CancellationToken,
    ) -> ExecutionResult:

        progress.begin_step("Scanning", total_items=0)
        progress.set_message(f"Scanning: {self._source_path.name}")

        if cancellation.is_cancelled:
            return ExecutionResult(success=False, message="Cancelled before scan started")

        try:
            scanner     = InputScanner()
            scan_result = scanner.scan(self._source_path)
        except Exception as error:
            return ExecutionResult(
                success = False,
                message = f"Scan failed: {error}",
                error   = error,
            )

        if cancellation.is_cancelled:
            return ExecutionResult(success=False, message="Cancelled after scan")

        progress.advance(item=str(self._source_path), increment=1)
        progress.set_message(f"Found {scan_result.file_count} files")

        return ExecutionResult(
            success = True,
            message = f"Scanned {scan_result.file_count} files",
            payload = scan_result,
            stats   = {
                "file_count":    scan_result.file_count,
                "total_size":    scan_result.total_size,
                "scan_duration": scan_result.scan_duration,
                "errors":        len(scan_result.errors),
            },
        )