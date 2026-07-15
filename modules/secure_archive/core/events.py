"""
modules/secure_archive/core/events.py

Archive domain event definitions and publishing helpers.

All Secure Archive domain events flow through the platform
Event Bus. Event payloads contain safe metadata only:
    - archive_id, archive_name, project_type
    - file_count, size stats, duration
    - timestamps
Never absolute paths, secrets, or full file content.
"""

from vaultcore.event_bus import platform_bus
from vaultcore.logger import log_event
from modules.secure_archive.models.reports import ArchiveReport
from modules.secure_archive.models.restore_result import RestoreReport


# Event name constants
EVENT_ANALYSIS_COMPLETED   = "archive.analysis_completed"
EVENT_CREATION_STARTED     = "archive.creation_started"
EVENT_CREATED              = "archive.created"
EVENT_CREATION_FAILED      = "archive.creation_failed"
EVENT_RESTORE_STARTED      = "archive.restore_started"
EVENT_RESTORED             = "archive.restored"
EVENT_RESTORE_FAILED       = "archive.restore_failed"
EVENT_INTEGRITY_FAILED     = "archive.integrity_failed"

# Sprint 15 encryption events
EVENT_ENCRYPTION_STARTED   = "archive.encryption_started"
EVENT_ENCRYPTION_COMPLETED = "archive.encryption_completed"
EVENT_DECRYPTION_STARTED   = "archive.decryption_started"
EVENT_DECRYPTION_COMPLETED = "archive.decryption_completed"
EVENT_AUTH_FAILED          = "archive.authentication_failed"


def publish_analysis_completed(
    archive_name: str,
    project_type: str,
    files_included: int,
    files_ignored: int
) -> None:
    """Publish archive.analysis_completed event."""
    platform_bus.publish(EVENT_ANALYSIS_COMPLETED, {
        "archive_name":   archive_name,
        "project_type":   project_type,
        "files_included": files_included,
        "files_ignored":  files_ignored,
    })
    log_event(
        "ArchiveAnalysisCompleted",
        f"{archive_name} ({project_type}): "
        f"{files_included} included, {files_ignored} ignored"
    )


def publish_creation_started(
    archive_name: str,
    project_type: str,
    file_count: int
) -> None:
    """Publish archive.creation_started event."""
    platform_bus.publish(EVENT_CREATION_STARTED, {
        "archive_name": archive_name,
        "project_type": project_type,
        "file_count":   file_count,
    })
    log_event(
        "ArchiveCreationStarted",
        f"{archive_name}: {file_count} files"
    )


def publish_created(report: ArchiveReport) -> None:
    """Publish archive.created event with full report metadata."""
    platform_bus.publish(EVENT_CREATED, {
        "archive_id":        report.archive_id,
        "archive_name":      report.archive_name,
        "project_type":      report.project_type,
        "file_count":        report.files_included,
        "original_size":     report.original_size,
        "compressed_size":   report.compressed_size,
        "compression_ratio": report.compression_ratio,
        "duration":          report.duration,
        "created_at":        report.created_at,
    })
    log_event(
        "ArchiveCreated",
        f"{report.archive_name}: "
        f"{report.files_included} files, "
        f"{report.compression_ratio:.1f}% saved"
    )


def publish_creation_failed(
    archive_name: str,
    error: str
) -> None:
    """Publish archive.creation_failed event."""
    platform_bus.publish(EVENT_CREATION_FAILED, {
        "archive_name": archive_name,
        "error":        error,
    })
    log_event(
        "ArchiveCreationFailed",
        f"{archive_name}: {error}"
    )


def publish_restore_started(
    archive_name: str,
    file_count: int
) -> None:
    """Publish archive.restore_started event."""
    platform_bus.publish(EVENT_RESTORE_STARTED, {
        "archive_name": archive_name,
        "file_count":   file_count,
    })
    log_event(
        "ArchiveRestoreStarted",
        f"{archive_name}: {file_count} files"
    )


def publish_restored(report: RestoreReport) -> None:
    """Publish archive.restored event."""
    platform_bus.publish(EVENT_RESTORED, {
        "archive_id":         report.archive_id,
        "archive_name":       report.archive_name,
        "files_expected":     report.files_expected,
        "files_verified":     report.files_verified,
        "integrity_failures": report.integrity_failures,
        "duration":           report.duration,
        "success":            report.success,
    })
    log_event(
        "ArchiveRestored",
        f"{report.archive_name}: "
        f"{report.files_verified}/{report.files_expected} verified"
    )


def publish_restore_failed(
    archive_name: str,
    error: str
) -> None:
    """Publish archive.restore_failed event."""
    platform_bus.publish(EVENT_RESTORE_FAILED, {
        "archive_name": archive_name,
        "error":        error,
    })
    log_event(
        "ArchiveRestoreFailed",
        f"{archive_name}: {error}"
    )


def publish_integrity_failed(
    archive_name: str,
    failures: int
) -> None:
    """Publish archive.integrity_failed event."""
    platform_bus.publish(EVENT_INTEGRITY_FAILED, {
        "archive_name":       archive_name,
        "integrity_failures": failures,
    })
    log_event(
        "ArchiveIntegrityFailed",
        f"{archive_name}: {failures} files failed integrity check"
    )


def publish_encryption_started(
    archive_name: str,
    file_count: int
) -> None:
    """Publish archive.encryption_started event."""
    platform_bus.publish(EVENT_ENCRYPTION_STARTED, {
        "archive_name": archive_name,
        "file_count":   file_count,
    })
    log_event(
        "ArchiveEncryptionStarted",
        f"{archive_name}: {file_count} files"
    )


def publish_encryption_completed(
    archive_name: str,
    file_size: int
) -> None:
    """Publish archive.encryption_completed event."""
    platform_bus.publish(EVENT_ENCRYPTION_COMPLETED, {
        "archive_name": archive_name,
        "file_size":    file_size,
    })
    log_event(
        "ArchiveEncryptionCompleted",
        f"{archive_name}: {file_size:,} bytes"
    )


def publish_decryption_started(archive_name: str) -> None:
    """Publish archive.decryption_started event."""
    platform_bus.publish(EVENT_DECRYPTION_STARTED, {
        "archive_name": archive_name,
    })
    log_event("ArchiveDecryptionStarted", archive_name)


def publish_decryption_completed(
    archive_name: str,
    files_restored: int
) -> None:
    """Publish archive.decryption_completed event."""
    platform_bus.publish(EVENT_DECRYPTION_COMPLETED, {
        "archive_name":   archive_name,
        "files_restored": files_restored,
    })
    log_event(
        "ArchiveDecryptionCompleted",
        f"{archive_name}: {files_restored} files"
    )


def publish_authentication_failed(archive_name: str) -> None:
    """Publish archive.authentication_failed event."""
    platform_bus.publish(EVENT_AUTH_FAILED, {
        "archive_name": archive_name,
    })
    log_event("ArchiveAuthenticationFailed", archive_name)
