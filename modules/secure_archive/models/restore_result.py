"""
modules/secure_archive/models/restore_result.py

Restoration result models.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RestoreFileResult:
    """
    Result of restoring one file.

    Attributes:
        relative_path:       Path from manifest.
        restored:            True if file was written.
        checksum_expected:   From manifest.
        checksum_actual:     Calculated after restore.
        integrity_verified:  True if checksums match.
        error:               Error message if failed.
        bytes_written:       Size of restored file.
    """
    relative_path:      str
    restored:           bool = False
    checksum_expected:  Optional[str] = None
    checksum_actual:    Optional[str] = None
    integrity_verified: bool = False
    error:              Optional[str] = None
    bytes_written:      int  = 0


@dataclass
class RestoreReport:
    """
    Complete restoration report.

    Attributes:
        archive_id:          From manifest.
        archive_name:        From manifest.
        destination_root:    Where files were restored.
        files_expected:      Manifest file count.
        files_restored:      Files successfully written.
        files_verified:      Files that passed integrity check.
        integrity_failures:  Files that failed integrity check.
        files_failed:        Files that could not be restored.
        results:             Per-file results.
        duration:            Total time in seconds.
        errors:              High-level error messages.
    """
    archive_id:          str
    archive_name:        str
    destination_root:    str
    files_expected:      int = 0
    files_restored:      int = 0
    files_verified:      int = 0
    integrity_failures:  int = 0
    files_failed:        int = 0
    results:             list[RestoreFileResult] = field(default_factory=list)
    duration:            float = 0.0
    errors:              list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """
        True only if all files restored AND all integrity checks passed.
        """
        return (
            self.files_expected > 0
            and self.files_restored  == self.files_expected
            and self.files_verified  == self.files_expected
            and self.integrity_failures == 0
            and self.files_failed    == 0
        )
