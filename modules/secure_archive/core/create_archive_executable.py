"""
modules/secure_archive/core/create_archive_executable.py

Executable wrapper for full encrypted archive creation.

Sprint 17 extension — moves compression + encryption to the
VaultCore ExecutionEngine so the UI stays responsive during
long-running archive creation.

Business logic (compression, manifest, payload, encryption)
is untouched. This file only wraps existing engines as an Executable.
"""

import io
import time
from pathlib import Path

from vaultcore.execution.interfaces.executable import Executable
from vaultcore.execution.interfaces.execution_result import ExecutionResult
from vaultcore.execution.progress.progress_tracker import ProgressTracker
from vaultcore.execution.cancellation.cancellation_token import CancellationToken

from modules.secure_archive.core.compression_engine import CompressionEngine
from modules.secure_archive.core.manifest_builder import ManifestBuilder
from modules.secure_archive.core.archive_payload import ArchivePayloadBuilder
from modules.secure_archive.core.sva_writer import SVAWriter


class CreateArchiveExecutable(Executable):
    """
    Runs the full encrypted archive creation pipeline on a worker thread.

    Pipeline:
        1. Compress all planned files
        2. Build manifest
        3. Build encrypted payload
        4. Write SVA file (AES-256-GCM)

    Result payload contains everything the dashboard needs to
    build the final report on the main thread.
    """

    def __init__(self, plan, password: str, output_path: Path) -> None:
        self._plan        = plan
        self._password    = password
        self._output_path = output_path

    def execute(
        self,
        progress: ProgressTracker,
        cancellation: CancellationToken,
    ) -> ExecutionResult:

        start = time.time()

        progress.begin_step("Compressing", total_items=self._plan.file_count)
        progress.set_message(f"Compressing {self._plan.file_count} files...")

        compressor = CompressionEngine()
        mbuilder   = ManifestBuilder()
        pbuilder   = ArchivePayloadBuilder()
        writer     = SVAWriter()

        try:
            buffers = {}

            def make_writer(path):
                buf = io.BytesIO()
                buffers[path] = buf
                return buf.write

            # ── Compression ──────────────────────────────────────────
            run_result = compressor.execute_plan(self._plan, make_writer)

            if cancellation.is_cancelled:
                return ExecutionResult(success=False, message="Cancelled after compression")

            # ── Manifest ─────────────────────────────────────────────
            progress.set_message("Building manifest...")
            manifest = mbuilder.build(self._plan, run_result)

            if cancellation.is_cancelled:
                return ExecutionResult(success=False, message="Cancelled after manifest")

            # ── Payload assembly ─────────────────────────────────────
            progress.set_message("Assembling encrypted payload...")
            compressed_entries = {p: b.getvalue() for p, b in buffers.items()}
            payload = pbuilder.build(manifest, compressed_entries)

            if cancellation.is_cancelled:
                return ExecutionResult(success=False, message="Cancelled before encryption")

            # ── Encryption + write ───────────────────────────────────
            progress.set_message("Encrypting and writing archive...")
            sva_result = writer.write(
                payload     = payload,
                password    = self._password,
                output_path = self._output_path
            )

        except Exception as error:
            return ExecutionResult(
                success = False,
                message = f"Archive creation failed: {error}",
                error   = error,
            )

        duration = time.time() - start

        progress.set_message(f"Complete in {duration:.2f}s")

        return ExecutionResult(
            success = True,
            message = f"Encrypted archive written to {self._output_path.name}",
            payload = {
                "plan":        self._plan,
                "manifest":    manifest,
                "run_result":  run_result,
                "sva_result":  sva_result,
                "output_path": self._output_path,
                "duration":    duration,
            },
            stats = {
                "file_count": self._plan.file_count,
                "duration":   duration,
                "file_size":  sva_result.file_size,
            },
        )