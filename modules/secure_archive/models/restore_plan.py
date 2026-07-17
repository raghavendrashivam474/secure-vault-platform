"""
modules/secure_archive/models/restore_plan.py

Restore planning models.

Describes what will be restored and where,
without performing any filesystem operations.
"""

from dataclasses import dataclass, field
from typing import Optional


# Restore mode constants
MODE_ORIGINAL_ROOT     = "original_root"      # Recreate archive root folder
MODE_CONTENTS_ONLY     = "contents_only"      # Extract contents without root
MODE_ORIGINAL_LOCATION = "original_location"  # Restore to original absolute path
MODE_CUSTOM            = "custom"             # User-specified destination


@dataclass
class RestorePlanEntry:
    """
    Describes one file to be restored.

    Attributes:
        manifest_path:     Relative path from manifest.
        destination_path:  Full absolute path where file will be written.
        size:              Expected file size.
        checksum:          Expected SHA-256 checksum.
    """
    manifest_path:     str
    destination_path:  str
    size:              int
    checksum:          str


@dataclass
class RestoreDirectoryEntry:
    """
    Describes one directory to be created.

    Attributes:
        relative_path:     Path relative to restore root.
        destination_path:  Full absolute path.
        is_empty:          True if this is an empty directory.
    """
    relative_path:     str
    destination_path:  str
    is_empty:          bool = False


@dataclass
class RestorePlan:
    """
    Complete restore plan.

    Describes everything that will happen during restoration
    without performing any operations.

    Attributes:
        archive_name:      Name of the archive being restored.
        archive_root:      Archive root folder name.
        restore_mode:      Selected restore mode.
        destination_root:  Base destination directory.
        restore_root:      Actual root of restoration (may include archive_root).
        directories:       Directories to create (in order).
        files:             Files to restore.
        total_files:       Count of files in plan.
        total_dirs:        Count of directories in plan.
        total_size:        Expected total bytes to restore.
    """
    archive_name:      str
    archive_root:      str
    restore_mode:      str
    destination_root:  str
    restore_root:      str
    directories:       list[RestoreDirectoryEntry] = field(default_factory=list)
    files:             list[RestorePlanEntry]      = field(default_factory=list)
    total_files:       int   = 0
    total_dirs:        int   = 0
    total_size:        int   = 0
