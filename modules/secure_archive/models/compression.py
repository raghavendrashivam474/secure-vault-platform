"""
modules/secure_archive/models/compression.py

Compression strategy models.
"""

from dataclasses import dataclass


# Compression strategy constants
STRATEGY_DEFLATE_HIGH   = "deflate_high"    # Maximum compression
STRATEGY_DEFLATE_NORMAL = "deflate_normal"  # Balanced
STRATEGY_DEFLATE_FAST   = "deflate_fast"    # Speed priority
STRATEGY_STORE          = "store"           # No compression


# Compression level mapping (used by zlib/zipfile)
STRATEGY_LEVELS = {
    STRATEGY_DEFLATE_HIGH:   9,
    STRATEGY_DEFLATE_NORMAL: 6,
    STRATEGY_DEFLATE_FAST:   3,
    STRATEGY_STORE:          0,
}


STRATEGY_LABELS = {
    STRATEGY_DEFLATE_HIGH:   "Deflate (High)",
    STRATEGY_DEFLATE_NORMAL: "Deflate (Normal)",
    STRATEGY_DEFLATE_FAST:   "Deflate (Fast)",
    STRATEGY_STORE:          "Store (No Compression)",
}


@dataclass
class CompressionDecision:
    """
    Represents a per-file compression strategy decision.

    Attributes:
        relative_path:     Path relative to scan root.
        file_class:        The file's classification.
        strategy:          Chosen compression strategy.
        compression_level: Numeric level (0-9).
        reason:            Why this strategy was chosen.
    """
    relative_path:     str
    file_class:        str
    strategy:          str
    compression_level: int
    reason:            str
