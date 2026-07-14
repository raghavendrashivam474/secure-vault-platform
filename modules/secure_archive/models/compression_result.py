"""
modules/secure_archive/models/compression_result.py

Compression execution result models.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompressionResult:
    """
    Result of compressing a single file.

    Attributes:
        relative_path:     Path relative to archive root.
        original_size:     Size before compression (bytes).
        compressed_size:   Size after compression (bytes).
        strategy:          Strategy that was used.
        checksum:          SHA-256 of original file contents.
        success:           True if compression succeeded.
        error:             Error message if failed.
    """
    relative_path:   str
    original_size:   int
    compressed_size: int
    strategy:        str
    checksum:        Optional[str] = None
    success:         bool          = True
    error:           Optional[str] = None

    @property
    def compression_ratio(self) -> float:
        """Return compression ratio as percentage (0-100)."""
        if self.original_size == 0:
            return 0.0
        return (1.0 - (self.compressed_size / self.original_size)) * 100


@dataclass
class CompressionRunResult:
    """
    Aggregate result of compressing all files in a plan.

    Attributes:
        results:          Per-file results.
        total_original:   Sum of original sizes.
        total_compressed: Sum of compressed sizes.
        successful:       Count of successful files.
        failed:           Count of failed files.
        duration:         Total time in seconds.
        errors:           Files that failed.
    """
    results:          list[CompressionResult] = field(default_factory=list)
    total_original:   int   = 0
    total_compressed: int   = 0
    successful:       int   = 0
    failed:           int   = 0
    duration:         float = 0.0
    errors:           list[str] = field(default_factory=list)

    @property
    def overall_ratio(self) -> float:
        """Return overall compression ratio."""
        if self.total_original == 0:
            return 0.0
        return (1.0 - (self.total_compressed / self.total_original)) * 100

    @property
    def space_saved(self) -> int:
        """Return bytes saved by compression."""
        return self.total_original - self.total_compressed
