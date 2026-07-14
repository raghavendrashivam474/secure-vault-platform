"""
modules/secure_archive/models/reports.py

Archive operation report models.
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ArchiveReport:
    """
    Summary report of an archive creation operation.

    Attributes:
        archive_id:            Unique archive UUID.
        archive_name:          Archive display name.
        project_type:          Detected project type.
        project_confidence:    Detection confidence.
        files_scanned:         Total files scanned.
        files_included:        Files that entered the archive.
        files_ignored:         Files excluded by ignore rules.
        original_size:         All scanned bytes.
        archived_input_size:   Bytes fed to compression.
        compressed_size:       Bytes in the final archive.
        space_saved:           original - compressed.
        compression_ratio:     Percentage savings (0-100).
        duration:              Total time in seconds.
        package_size:          .sva.dev file size on disk.
        created_at:            ISO 8601 timestamp.
    """
    archive_id:          str
    archive_name:        str
    project_type:        str
    project_confidence:  str
    files_scanned:       int   = 0
    files_included:      int   = 0
    files_ignored:       int   = 0
    original_size:       int   = 0
    archived_input_size: int   = 0
    compressed_size:     int   = 0
    space_saved:         int   = 0
    compression_ratio:   float = 0.0
    duration:            float = 0.0
    package_size:        int   = 0
    created_at:          str   = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def formatted_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 ** 3:
            return f"{size_bytes / (1024 ** 2):.1f} MB"
        else:
            return f"{size_bytes / (1024 ** 3):.2f} GB"
