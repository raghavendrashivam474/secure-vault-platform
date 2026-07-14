"""
modules/secure_archive/core/compression_strategy.py

Assigns compression strategies based on file classification.

Rules are deterministic. Already-compressed formats (images,
video, archives) get STORE to avoid wasted CPU cycles.
"""

from modules.secure_archive.models.classification import (
    FileClassification,
    CLASS_TEXT, CLASS_STRUCTURED_TEXT, CLASS_SOURCE_CODE,
    CLASS_DOCUMENT, CLASS_IMAGE, CLASS_AUDIO, CLASS_VIDEO,
    CLASS_ARCHIVE, CLASS_BINARY, CLASS_UNKNOWN
)
from modules.secure_archive.models.compression import (
    CompressionDecision,
    STRATEGY_DEFLATE_HIGH, STRATEGY_DEFLATE_NORMAL,
    STRATEGY_DEFLATE_FAST, STRATEGY_STORE,
    STRATEGY_LEVELS
)


# Strategy mapping per file class
CLASS_STRATEGY = {
    CLASS_SOURCE_CODE:     STRATEGY_DEFLATE_HIGH,
    CLASS_TEXT:            STRATEGY_DEFLATE_HIGH,
    CLASS_STRUCTURED_TEXT: STRATEGY_DEFLATE_HIGH,
    CLASS_DOCUMENT:        STRATEGY_DEFLATE_NORMAL,
    CLASS_BINARY:          STRATEGY_DEFLATE_FAST,
    CLASS_IMAGE:           STRATEGY_STORE,
    CLASS_AUDIO:           STRATEGY_STORE,
    CLASS_VIDEO:           STRATEGY_STORE,
    CLASS_ARCHIVE:         STRATEGY_STORE,
    CLASS_UNKNOWN:         STRATEGY_DEFLATE_NORMAL,
}


# Reason messages for transparency
REASON_MESSAGES = {
    CLASS_SOURCE_CODE:
        "Source code compresses very well with maximum deflate.",
    CLASS_TEXT:
        "Plain text compresses excellently with maximum deflate.",
    CLASS_STRUCTURED_TEXT:
        "Structured text (JSON/YAML/XML) has high redundancy.",
    CLASS_DOCUMENT:
        "Documents may contain some pre-compressed content.",
    CLASS_BINARY:
        "Binary files often contain compressible sections.",
    CLASS_IMAGE:
        "Image is already compressed. STORE avoids wasted CPU.",
    CLASS_AUDIO:
        "Audio is already compressed. STORE avoids wasted CPU.",
    CLASS_VIDEO:
        "Video is already compressed. STORE avoids wasted CPU.",
    CLASS_ARCHIVE:
        "Archive is already compressed. STORE avoids wasted CPU.",
    CLASS_UNKNOWN:
        "Unknown format. Normal compression chosen as safe default.",
}


class CompressionStrategyEngine:
    """
    Assigns compression strategies to classified files.

    Deterministic rules. Never compresses data.
    """

    def decide(self, classification: FileClassification) -> CompressionDecision:
        """
        Choose a compression strategy for a classified file.

        Args:
            classification: The file classification.

        Returns:
            A CompressionDecision with strategy and reason.
        """
        strategy = CLASS_STRATEGY.get(
            classification.file_class, STRATEGY_DEFLATE_NORMAL
        )
        level  = STRATEGY_LEVELS[strategy]
        reason = REASON_MESSAGES.get(
            classification.file_class,
            "Default strategy applied."
        )

        return CompressionDecision(
            relative_path     = classification.relative_path,
            file_class        = classification.file_class,
            strategy          = strategy,
            compression_level = level,
            reason            = reason
        )

    def decide_all(
        self,
        classifications: list[FileClassification]
    ) -> list[CompressionDecision]:
        """
        Assign strategies to a list of classifications.

        Args:
            classifications: List of file classifications.

        Returns:
            List of compression decisions in same order.
        """
        return [self.decide(c) for c in classifications]

    def summarize(
        self,
        decisions: list[CompressionDecision]
    ) -> dict[str, int]:
        """
        Count decisions by strategy.

        Args:
            decisions: List of compression decisions.

        Returns:
            Dictionary mapping strategy to count.
        """
        counts = {}
        for d in decisions:
            counts[d.strategy] = counts.get(d.strategy, 0) + 1
        return counts
