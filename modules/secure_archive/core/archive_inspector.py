"""
modules/secure_archive/core/archive_inspector.py

Archive inspection and restore report generation.

ArchiveInspector provides metadata preview before restoration.
RestoreReportBuilder generates comprehensive post-restore reports.
"""

from dataclasses import dataclass, field
from typing import Optional

from modules.secure_archive.models.manifest import ArchiveManifest
from modules.secure_archive.models.header import SVAHeader
from modules.secure_archive.models.restore_session import RestoreSession
from modules.secure_archive.core.integrity_validator import IntegrityReport


@dataclass
class ArchiveInspection:
    """
    Preview of archive contents before restoration.

    Attributes:
        archive_name:        Display name.
        archive_id:          UUID.
        module_version:      Secure Archive version.
        format_version:      Manifest format version.
        project_type:        Detected project type.
        archive_root:        Root folder name.
        original_path:       Original source path.
        file_count:          Total files.
        directory_count:     Total directories from manifest.
        empty_dir_count:     Empty directories.
        original_size:       Sum of original file sizes.
        compressed_size:     Sum of compressed sizes.
        compression_ratio:   Percentage saved.
        encryption:          Encryption algorithm.
        kdf:                 Key derivation function.
        kdf_iterations:      PBKDF2 iterations.
        created_at:          Archive creation timestamp.
    """
    archive_name:      str   = ""
    archive_id:        str   = ""
    module_version:    str   = ""
    format_version:    int   = 0
    project_type:      str   = ""
    archive_root:      str   = ""
    original_path:     str   = ""
    file_count:        int   = 0
    directory_count:   int   = 0
    empty_dir_count:   int   = 0
    original_size:     int   = 0
    compressed_size:   int   = 0
    compression_ratio: float = 0.0
    encryption:        str   = ""
    kdf:               str   = ""
    kdf_iterations:    int   = 0
    created_at:        str   = ""


class ArchiveInspector:
    """
    Inspects archive metadata without decrypting payload.
    """

    def inspect_from_manifest(
        self,
        manifest: ArchiveManifest,
        header: Optional[SVAHeader] = None
    ) -> ArchiveInspection:
        """
        Build an inspection from manifest and optional header.

        Args:
            manifest: The archive manifest.
            header:   Optional SVA header for encryption info.

        Returns:
            ArchiveInspection with complete metadata.
        """
        ratio = 0.0
        if manifest.original_size > 0:
            ratio = (1 - manifest.compressed_size / manifest.original_size) * 100

        return ArchiveInspection(
            archive_name      = manifest.archive_name,
            archive_id        = manifest.archive_id,
            module_version    = manifest.module_version,
            format_version    = manifest.format_version,
            project_type      = manifest.project_type,
            archive_root      = manifest.archive_root,
            original_path     = manifest.original_source_path,
            file_count        = manifest.file_count,
            directory_count   = len(manifest.directory_paths),
            empty_dir_count   = manifest.empty_directory_count,
            original_size     = manifest.original_size,
            compressed_size   = manifest.compressed_size,
            compression_ratio = ratio,
            encryption        = header.encryption_algorithm if header else "",
            kdf               = header.kdf_algorithm if header else "",
            kdf_iterations    = header.kdf_iterations if header else 0,
            created_at        = manifest.created_at,
        )


@dataclass
class RestoreReport:
    """
    Comprehensive post-restore report.

    Attributes:
        session_id:         Restore session ID.
        archive_name:       Archive that was restored.
        archive_id:         Archive UUID.
        restore_mode:       Mode used.
        destination:        Restore destination.
        dirs_created:       Directories created.
        dirs_existed:       Directories that already existed.
        dirs_failed:        Directories that failed.
        files_restored:     Files successfully written.
        files_skipped:      Files skipped (conflicts).
        files_overwritten:  Files overwritten.
        files_renamed:      Files renamed.
        files_failed:       Files that failed.
        bytes_restored:     Total bytes written.
        verified_count:     Files that passed integrity check.
        failed_count:       Files that failed integrity check.
        missing_count:      Files not found after restore.
        integrity_success:  True if all files verified.
        warnings:           Non-fatal warnings.
        errors:             Error messages.
        elapsed:            Total time in seconds.
        overall_success:    True if everything passed.
    """
    session_id:        str   = ""
    archive_name:      str   = ""
    archive_id:        str   = ""
    restore_mode:      str   = ""
    destination:       str   = ""
    dirs_created:      int   = 0
    dirs_existed:      int   = 0
    dirs_failed:       int   = 0
    files_restored:    int   = 0
    files_skipped:     int   = 0
    files_overwritten: int   = 0
    files_renamed:     int   = 0
    files_failed:      int   = 0
    bytes_restored:    int   = 0
    verified_count:    int   = 0
    failed_count:      int   = 0
    missing_count:     int   = 0
    integrity_success: bool  = False
    warnings:          list[str] = field(default_factory=list)
    errors:            list[str] = field(default_factory=list)
    elapsed:           float     = 0.0
    overall_success:   bool      = False


class RestoreReportBuilder:
    """
    Builds a RestoreReport from session and integrity results.
    """

    def build(
        self,
        session: RestoreSession,
        integrity: IntegrityReport
    ) -> RestoreReport:
        """
        Build the final restore report.

        Args:
            session:   The completed RestoreSession.
            integrity: The integrity verification report.

        Returns:
            A comprehensive RestoreReport.
        """
        overall_success = (
            session.files_failed == 0
            and session.dirs_failed == 0
            and integrity.success
        )

        warnings = [w.message for w in session.warnings]
        errors   = list(session.errors)

        if not integrity.success:
            errors.append(
                f"Integrity verification failed: "
                f"{integrity.failed} mismatches, "
                f"{integrity.missing} missing"
            )

        return RestoreReport(
            session_id        = session.session_id,
            archive_name      = session.archive_name,
            archive_id        = session.archive_id,
            restore_mode      = session.restore_mode,
            destination       = session.restore_root,
            dirs_created      = session.dirs_created,
            dirs_existed      = session.dirs_skipped,
            dirs_failed       = session.dirs_failed,
            files_restored    = session.files_restored,
            files_skipped     = session.files_skipped,
            files_overwritten = session.files_overwritten,
            files_renamed     = session.files_renamed,
            files_failed      = session.files_failed,
            bytes_restored    = session.bytes_restored,
            verified_count    = integrity.verified,
            failed_count      = integrity.failed,
            missing_count     = integrity.missing,
            integrity_success = integrity.success,
            warnings          = warnings,
            errors            = errors,
            elapsed           = session.elapsed,
            overall_success   = overall_success,
        )
