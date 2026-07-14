"""
modules/secure_archive/models/archive_plan.py

Archive execution plan model.

The plan is the immutable source of truth for compression.
Once created, the compression engine executes it exactly.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

from modules.secure_archive.models.project import ProjectProfile


@dataclass
class ArchivePlanEntry:
    """
    Represents one file to be archived.

    Attributes:
        source_path:           Absolute source file path.
        relative_path:         Path relative to archive root.
        size:                  File size in bytes.
        file_class:            File classification.
        compression_strategy:  Assigned strategy.
        compression_level:     Numeric compression level.
        strategy_reason:       Why this strategy was chosen.
    """
    source_path:           str
    relative_path:         str
    size:                  int
    file_class:            str
    compression_strategy:  str
    compression_level:     int
    strategy_reason:       str


@dataclass
class ArchivePlan:
    """
    Complete archive execution plan.

    Attributes:
        archive_name:         Suggested archive name.
        source_root:          Absolute path to scan root.
        project_profile:      Detected project type.
        included_files:       Files to be archived.
        ignored_files:        Files marked as ignored (metadata only).
        total_original_size:  All scanned bytes.
        included_size:        Bytes to be archived.
        ignored_size:         Bytes to be skipped.
        strategy_summary:     Count of files per strategy.
        class_summary:        Count of files per class.
        ignore_summary:       Count of ignored files per rule.
        created_at:           ISO 8601 timestamp.
    """
    archive_name:         str
    source_root:          str
    project_profile:      ProjectProfile
    included_files:       list[ArchivePlanEntry]     = field(default_factory=list)
    ignored_files:        list[dict]                 = field(default_factory=list)
    total_original_size:  int                        = 0
    included_size:        int                        = 0
    ignored_size:         int                        = 0
    strategy_summary:     dict[str, int]             = field(default_factory=dict)
    class_summary:        dict[str, int]             = field(default_factory=dict)
    ignore_summary:       dict[str, int]             = field(default_factory=dict)
    created_at:           str                        = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def file_count(self) -> int:
        """Number of files that will be archived."""
        return len(self.included_files)

    @property
    def ignored_count(self) -> int:
        """Number of files that will be excluded."""
        return len(self.ignored_files)

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
