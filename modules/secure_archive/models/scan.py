"""
modules/secure_archive/models/scan.py

Input scan result models.

Describes filesystem content only.
No classification, ignore, or compression logic here.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ScannedFile:
    """
    Represents a single scanned file.

    Attributes:
        absolute_source_path: Full absolute path on the filesystem.
        relative_path:        Path relative to scan root (forward slashes).
        filename:             The filename portion.
        extension:            File extension (lowercase, no leading dot).
        size:                 File size in bytes.
        modified_time:        Last modification timestamp (ISO 8601).
    """
    absolute_source_path: str
    relative_path:        str
    filename:             str
    extension:            str
    size:                 int
    modified_time:        str


@dataclass
class ScanResult:
    """
    Complete scan result for one archive input.

    Attributes:
        source_root:    Absolute path of the scan root.
        source_type:    'file' or 'folder'.
        files:          All discovered files.
        file_count:     Total files found.
        total_size:     Sum of all file sizes in bytes.
        scan_duration:  Scan duration in seconds.
        errors:         List of paths that could not be read.
    """
    source_root:    str
    source_type:    str
    files:          list[ScannedFile] = field(default_factory=list)
    file_count:     int   = 0
    total_size:     int   = 0
    scan_duration:  float = 0.0
    errors:         list[str] = field(default_factory=list)

    def formatted_size(self) -> str:
        """Return total size as human-readable string."""
        size = self.total_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 ** 3:
            return f"{size / (1024 ** 2):.1f} MB"
        else:
            return f"{size / (1024 ** 3):.2f} GB"
