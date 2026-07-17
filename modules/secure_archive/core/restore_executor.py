"""
modules/secure_archive/core/restore_executor.py

Executes a validated RestorePlan using a RestoreSession.

Performs the actual filesystem restoration. Never plans.
All planning has already happened in Part 1.

Pipeline:
    RestorePlan → DirectoryCreator → File Restoration → Session Updated
"""

import time
from pathlib import Path
from typing import Optional, Callable

from modules.secure_archive.models.restore_plan import RestorePlan
from modules.secure_archive.models.restore_session import (
    RestoreSession, STATUS_RUNNING, STATUS_FAILED
)
from modules.secure_archive.core.directory_creator import DirectoryCreator
from modules.secure_archive.core.decompression_engine import DecompressionEngine
from modules.secure_archive.core.path_validator import PathValidator
from vaultcore.logger import log_debug, log_error, log_event


class RestoreExecutor:
    """
    Executes a validated RestorePlan.

    Does NOT plan. Does NOT detect conflicts.
    Only executes what the plan says to do.

    Uses RestoreSession as the central state object.
    """

    def __init__(self) -> None:
        self._dir_creator   = DirectoryCreator()
        self._decompressor  = DecompressionEngine()
        self._path_validator = PathValidator()

    def execute(
        self,
        plan: RestorePlan,
        session: RestoreSession,
        get_compressed_data: Callable[[str], Optional[bytes]],
        get_strategy: Callable[[str], str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> RestoreSession:
        """
        Execute a restore plan.

        Args:
            plan:                The validated RestorePlan.
            session:             The RestoreSession to update.
            get_compressed_data: Callable(manifest_path) -> compressed bytes.
            get_strategy:        Callable(manifest_path) -> compression strategy.
            progress_callback:   Optional progress(current, total, path).

        Returns:
            The updated RestoreSession.
        """
        session.start()
        session.files_expected = plan.total_files
        session.bytes_expected = plan.total_size

        log_event(
            "RestoreExecutionStarted",
            f"Session {session.session_id}: {plan.total_files} files"
        )

        # Step 1: Create directories
        try:
            dir_result = self._dir_creator.create_from_plan(plan)
            session.dirs_created = dir_result.created
            session.dirs_skipped = dir_result.already_existed
            session.dirs_failed  = dir_result.failed

            if not dir_result.success:
                for error in dir_result.errors:
                    session.errors.append(f"Directory: {error}")
        except Exception as error:
            session.fail(f"Directory creation failed: {error}")
            return session

        # Step 2: Restore files
        restore_root = Path(plan.restore_root)
        total = len(plan.files)

        for index, entry in enumerate(plan.files, 1):
            if progress_callback:
                progress_callback(index, total, entry.manifest_path)

            file_start = time.time()

            try:
                self._restore_one_file(
                    entry, restore_root, session,
                    get_compressed_data, get_strategy
                )
            except Exception as error:
                session.record_file_failed(
                    entry.manifest_path, str(error)
                )
                log_error(
                    f"[RestoreExecutor] Failed: {entry.manifest_path}: {error}"
                )

        log_event(
            "RestoreExecutionFinished",
            f"Session {session.session_id}: "
            f"{session.files_restored}/{session.files_expected}"
        )

        return session

    def _restore_one_file(
        self,
        entry,
        restore_root: Path,
        session: RestoreSession,
        get_compressed_data: Callable,
        get_strategy: Callable
    ) -> None:
        """Restore a single file from the plan."""
        file_start = time.time()
        dest_path  = Path(entry.destination_path)

        # Validate destination path
        validation = self._path_validator.validate(
            entry.manifest_path, restore_root
        )
        if not validation.is_safe:
            session.record_file_failed(
                entry.manifest_path,
                f"Unsafe path: {validation.rejection_reason}"
            )
            return

        # Get compressed data
        compressed = get_compressed_data(entry.manifest_path)
        if compressed is None:
            session.record_file_failed(
                entry.manifest_path, "Compressed data not found"
            )
            return

        # Get compression strategy
        strategy = get_strategy(entry.manifest_path)

        # Decompress
        decompressed = self._decompressor.decompress(compressed, strategy)
        if decompressed is None:
            session.record_file_failed(
                entry.manifest_path, "Decompression failed"
            )
            return

        # Ensure parent directory exists
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            session.record_file_failed(
                entry.manifest_path,
                f"Cannot create parent directory: {error}"
            )
            return

        # Write file
        try:
            dest_path.write_bytes(decompressed)
        except OSError as error:
            session.record_file_failed(
                entry.manifest_path, f"Write failed: {error}"
            )
            return

        # Record success
        duration = time.time() - file_start
        session.record_file_restored(
            manifest_path    = entry.manifest_path,
            destination_path = str(dest_path),
            bytes_written    = len(decompressed),
            duration         = duration
        )
