"""
modules/secure_archive/core/integrity_validator.py

Post-restore integrity verification.

Verifies every restored file against manifest SHA-256 checksums.
Updates RestoreSession with verification results.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from modules.secure_archive.models.manifest import ArchiveManifest
from modules.secure_archive.models.restore_session import RestoreSession
from modules.secure_archive.core.checksum_engine import ChecksumEngine
from vaultcore.logger import log_debug, log_error, log_event


@dataclass
class IntegrityResult:
    """
    Result of verifying one restored file.

    Attributes:
        manifest_path:      File path from manifest.
        expected_checksum:  Manifest SHA-256.
        actual_checksum:    Computed SHA-256.
        verified:           True if checksums match.
        file_exists:        True if file was found at destination.
        error:              Error message if verification failed.
    """
    manifest_path:     str
    expected_checksum: str
    actual_checksum:   Optional[str] = None
    verified:          bool          = False
    file_exists:       bool          = True
    error:             Optional[str] = None


@dataclass
class IntegrityReport:
    """
    Summary of all integrity checks.

    Attributes:
        total_files:      Files checked.
        verified:         Files that passed.
        failed:           Files that failed.
        missing:          Files not found on disk.
        results:          Per-file results.
    """
    total_files: int = 0
    verified:    int = 0
    failed:      int = 0
    missing:     int = 0
    results:     list[IntegrityResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if all files verified successfully."""
        return self.failed == 0 and self.missing == 0


class IntegrityValidator:
    """
    Verifies restored files against manifest checksums.

    Updates the RestoreSession verification state.
    """

    def __init__(self) -> None:
        self._checksum = ChecksumEngine()

    def verify(
        self,
        session: RestoreSession,
        manifest: ArchiveManifest,
    ) -> IntegrityReport:
        """
        Verify all restored files against manifest.

        Args:
            session:   The RestoreSession with restored file paths.
            manifest:  The manifest with expected checksums.

        Returns:
            IntegrityReport with per-file results.
        """
        session.begin_verification()

        report = IntegrityReport()

        # Build lookup: manifest_path -> destination_path
        dest_lookup = {}
        for entry in session.restored_entries:
            dest_lookup[entry.manifest_path] = entry.destination_path

        log_event(
            "IntegrityVerificationStarted",
            f"Session {session.session_id}: {len(manifest.files)} files"
        )

        for manifest_entry in manifest.files:
            dest_path_str = dest_lookup.get(manifest_entry.path)

            if dest_path_str is None:
                # File was not restored (skipped or failed)
                result = IntegrityResult(
                    manifest_path     = manifest_entry.path,
                    expected_checksum = manifest_entry.checksum,
                    file_exists       = False,
                    error             = "File was not restored"
                )
                report.missing += 1
                report.results.append(result)
                continue

            dest_path = Path(dest_path_str)

            if not dest_path.exists():
                result = IntegrityResult(
                    manifest_path     = manifest_entry.path,
                    expected_checksum = manifest_entry.checksum,
                    file_exists       = False,
                    error             = "Restored file not found on disk"
                )
                report.missing += 1
                report.results.append(result)
                continue

            # Compute checksum
            actual = self._checksum.compute(dest_path)

            if actual is None:
                result = IntegrityResult(
                    manifest_path     = manifest_entry.path,
                    expected_checksum = manifest_entry.checksum,
                    file_exists       = True,
                    error             = "Failed to compute checksum"
                )
                report.failed += 1
                report.results.append(result)
                continue

            # Compare
            matches = (actual == manifest_entry.checksum)

            result = IntegrityResult(
                manifest_path     = manifest_entry.path,
                expected_checksum = manifest_entry.checksum,
                actual_checksum   = actual,
                verified          = matches,
                file_exists       = True
            )

            if matches:
                report.verified += 1
            else:
                report.failed += 1
                result.error = "Checksum mismatch"
                log_error(
                    f"[IntegrityValidator] Mismatch: {manifest_entry.path} "
                    f"expected {manifest_entry.checksum[:16]}... "
                    f"got {actual[:16]}..."
                )

            report.results.append(result)

        report.total_files = len(report.results)

        log_event(
            "IntegrityVerificationFinished",
            f"{report.verified}/{report.total_files} verified"
        )

        return report
