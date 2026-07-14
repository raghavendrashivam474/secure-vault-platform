"""
modules/secure_archive/core/restore_engine.py

Verified archive restoration engine.

Flow:
    1. Open package
    2. Load manifest
    3. Validate manifest version
    4. For each file:
        a. Validate path
        b. Create parent directories
        c. Read compressed payload
        d. Decompress
        e. Write file
        f. Compute checksum
        g. Compare against manifest
    5. Return report
"""

import time
from pathlib import Path
from typing import Optional, Callable

from modules.secure_archive.core.package_reader import PackageReader
from modules.secure_archive.core.path_validator import PathValidator
from modules.secure_archive.core.decompression_engine import DecompressionEngine
from modules.secure_archive.core.checksum_engine import ChecksumEngine
from modules.secure_archive.models.restore_result import (
    RestoreFileResult, RestoreReport
)
from vaultcore.logger import log_debug, log_error, log_event


class RestoreEngine:
    """
    Executes verified archive restoration.

    Every restored file is checksum-verified against the manifest.
    Path traversal attempts are rejected.
    Original directory hierarchy is reconstructed exactly.
    """

    def __init__(self) -> None:
        self._path_validator = PathValidator()
        self._decompressor   = DecompressionEngine()
        self._checksum       = ChecksumEngine()

    def restore(
        self,
        package_path: Path,
        destination_root: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> RestoreReport:
        """
        Restore an archive package to a destination directory.

        Args:
            package_path:      Path to the .sva.dev file.
            destination_root:  Root directory for restoration.
            progress_callback: Optional callback(current, total, path).

        Returns:
            A RestoreReport with per-file results.
        """
        start = time.time()

        # Ensure destination exists
        destination_root.mkdir(parents=True, exist_ok=True)
        destination_root = destination_root.resolve()

        report = RestoreReport(
            archive_id       = "",
            archive_name     = "",
            destination_root = str(destination_root)
        )

        # Open package
        try:
            reader = PackageReader(package_path)
        except (FileNotFoundError, ValueError) as error:
            report.errors.append(str(error))
            report.duration = time.time() - start
            return report

        try:
            # Read manifest
            try:
                manifest = reader.read_manifest()
            except ValueError as error:
                report.errors.append(f"Manifest error: {error}")
                report.duration = time.time() - start
                return report

            report.archive_id     = manifest.archive_id
            report.archive_name   = manifest.archive_name
            report.files_expected = manifest.file_count

            log_event(
                "ArchiveRestoreStarted",
                f"{manifest.archive_name} ({manifest.file_count} files)"
            )

            total = manifest.file_count

            # Process each file
            for index, entry in enumerate(manifest.files, 1):
                if progress_callback:
                    progress_callback(index, total, entry.path)

                result = self._restore_one_file(
                    reader, entry, destination_root
                )
                report.results.append(result)

                if result.restored:
                    report.files_restored += 1
                    if result.integrity_verified:
                        report.files_verified += 1
                    else:
                        report.integrity_failures += 1
                else:
                    report.files_failed += 1

        finally:
            reader.close()

        report.duration = time.time() - start

        log_event(
            "ArchiveRestoreFinished",
            f"{report.files_verified}/{report.files_expected} verified"
        )

        return report

    def _restore_one_file(
        self,
        reader: PackageReader,
        manifest_entry,
        destination_root: Path
    ) -> RestoreFileResult:
        """Restore and verify a single file entry."""
        result = RestoreFileResult(
            relative_path     = manifest_entry.path,
            checksum_expected = manifest_entry.checksum
        )

        # Validate path
        validation = self._path_validator.validate(
            manifest_entry.path, destination_root
        )

        if not validation.is_safe:
            result.error = f"Unsafe path: {validation.rejection_reason}"
            log_error(
                f"[RestoreEngine] Rejected {manifest_entry.path}: "
                f"{validation.rejection_reason}"
            )
            return result

        output_path = validation.resolved_path

        # Read compressed payload
        compressed = reader.read_payload(manifest_entry.path)
        if compressed is None:
            result.error = "Payload not found in package"
            return result

        # Decompress
        decompressed = self._decompressor.decompress(
            compressed, manifest_entry.compression_strategy
        )
        if decompressed is None:
            result.error = "Decompression failed"
            return result

        # Ensure parent directory exists
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            result.error = f"Cannot create parent directory: {error}"
            return result

        # Write file
        try:
            output_path.write_bytes(decompressed)
            result.restored      = True
            result.bytes_written = len(decompressed)
        except OSError as error:
            result.error = f"Write failed: {error}"
            return result

        # Verify checksum
        actual = self._checksum.compute(output_path)
        result.checksum_actual = actual

        if actual is None:
            result.error = "Failed to compute restored file checksum"
            return result

        result.integrity_verified = (actual == manifest_entry.checksum)

        if not result.integrity_verified:
            log_error(
                f"[RestoreEngine] Integrity failure on {manifest_entry.path}: "
                f"expected {manifest_entry.checksum[:16]}..., "
                f"got {actual[:16]}..."
            )

        return result
