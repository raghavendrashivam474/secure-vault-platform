"""
modules/secure_archive/models/restore_session.py

Restore Session — the central runtime object for a restore operation.

All Part 2 components operate on this session rather than
passing multiple objects between them.
"""

import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# Session status constants
STATUS_INITIALIZED = "initialized"
STATUS_RUNNING     = "running"
STATUS_VERIFYING   = "verifying"
STATUS_COMPLETED   = "completed"
STATUS_FAILED      = "failed"


@dataclass
class RestoredEntry:
    """
    Tracks one successfully restored file.

    Attributes:
        manifest_path:    Path from manifest.
        destination_path: Where file was written.
        bytes_written:    Bytes actually written.
        duration:         Time to restore this file in seconds.
    """
    manifest_path:    str
    destination_path: str
    bytes_written:    int   = 0
    duration:         float = 0.0


@dataclass
class RestoreWarning:
    """
    A non-fatal issue during restoration.

    Attributes:
        file_path:  Affected file path.
        message:    Warning description.
        category:   Warning category (e.g. 'conflict', 'permission').
    """
    file_path: str
    message:   str
    category:  str = "general"


@dataclass
class RestoreSession:
    """
    Central runtime object for a restore operation.

    Tracks the entire lifecycle from initialization to completion.
    All Part 2 components update this session.

    Attributes:
        session_id:       Unique session identifier.
        archive_name:     Name of the archive being restored.
        archive_id:       Archive UUID from manifest.
        restore_mode:     Selected restore mode.
        destination_root: User-chosen destination.
        restore_root:     Actual root path for restoration.
        status:           Current session status.
        start_time:       When restoration started (epoch).
        end_time:         When restoration finished (epoch).
        dirs_created:     Directories successfully created.
        dirs_skipped:     Directories that already existed.
        dirs_failed:      Directories that failed to create.
        files_expected:   Total files in plan.
        files_restored:   Files successfully written.
        files_skipped:    Files skipped (conflict resolution).
        files_failed:     Files that failed to restore.
        files_overwritten: Files overwritten (conflict resolution).
        files_renamed:    Files renamed (conflict resolution).
        bytes_restored:   Total bytes written.
        bytes_expected:   Total bytes expected.
        restored_entries: Individual file results.
        warnings:         Non-fatal issues.
        errors:           Fatal error messages.
    """
    session_id:       str  = ""
    archive_name:     str  = ""
    archive_id:       str  = ""
    restore_mode:     str  = ""
    destination_root: str  = ""
    restore_root:     str  = ""
    status:           str  = STATUS_INITIALIZED
    start_time:       float = 0.0
    end_time:         float = 0.0
    dirs_created:     int  = 0
    dirs_skipped:     int  = 0
    dirs_failed:      int  = 0
    files_expected:   int  = 0
    files_restored:   int  = 0
    files_skipped:    int  = 0
    files_failed:     int  = 0
    files_overwritten: int = 0
    files_renamed:    int  = 0
    bytes_restored:   int  = 0
    bytes_expected:   int  = 0
    restored_entries: list[RestoredEntry]  = field(default_factory=list)
    warnings:         list[RestoreWarning] = field(default_factory=list)
    errors:           list[str]            = field(default_factory=list)

    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())[:8]

    @property
    def elapsed(self) -> float:
        """Seconds elapsed since start."""
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    @property
    def progress_percent(self) -> float:
        """Completion percentage (0-100)."""
        if self.files_expected == 0:
            return 100.0
        return (self.files_restored / self.files_expected) * 100

    @property
    def is_complete(self) -> bool:
        """True if session finished (success or failure)."""
        return self.status in (STATUS_COMPLETED, STATUS_FAILED)

    @property
    def success(self) -> bool:
        """True only if completed with no failures."""
        return (
            self.status == STATUS_COMPLETED
            and self.files_failed == 0
            and self.dirs_failed == 0
        )

    def start(self) -> None:
        """Mark session as running."""
        self.status     = STATUS_RUNNING
        self.start_time = time.time()

    def begin_verification(self) -> None:
        """Transition to verification phase."""
        self.status = STATUS_VERIFYING

    def complete(self) -> None:
        """Mark session as completed."""
        self.status   = STATUS_COMPLETED
        self.end_time = time.time()

    def fail(self, error: str) -> None:
        """Mark session as failed."""
        self.status   = STATUS_FAILED
        self.end_time = time.time()
        self.errors.append(error)

    def record_file_restored(
        self,
        manifest_path: str,
        destination_path: str,
        bytes_written: int,
        duration: float
    ) -> None:
        """Record a successfully restored file."""
        self.files_restored += 1
        self.bytes_restored += bytes_written
        self.restored_entries.append(RestoredEntry(
            manifest_path    = manifest_path,
            destination_path = destination_path,
            bytes_written    = bytes_written,
            duration         = duration
        ))

    def record_file_failed(self, manifest_path: str, error: str) -> None:
        """Record a file that failed to restore."""
        self.files_failed += 1
        self.errors.append(f"{manifest_path}: {error}")

    def record_file_skipped(self, manifest_path: str, reason: str) -> None:
        """Record a skipped file."""
        self.files_skipped += 1
        self.warnings.append(RestoreWarning(
            file_path = manifest_path,
            message   = reason,
            category  = "skipped"
        ))

    def add_warning(self, file_path: str, message: str, category: str = "general") -> None:
        """Add a non-fatal warning."""
        self.warnings.append(RestoreWarning(
            file_path = file_path,
            message   = message,
            category  = category
        ))
