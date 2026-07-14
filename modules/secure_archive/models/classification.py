"""
modules/secure_archive/models/classification.py

File classification models.
"""

from dataclasses import dataclass


# File class constants
CLASS_TEXT             = "text"
CLASS_STRUCTURED_TEXT  = "structured_text"
CLASS_SOURCE_CODE      = "source_code"
CLASS_DOCUMENT         = "document"
CLASS_IMAGE            = "image"
CLASS_AUDIO            = "audio"
CLASS_VIDEO            = "video"
CLASS_ARCHIVE          = "archive"
CLASS_BINARY           = "binary"
CLASS_UNKNOWN          = "unknown"


CLASS_LABELS = {
    CLASS_TEXT:             "Text",
    CLASS_STRUCTURED_TEXT:  "Structured Text",
    CLASS_SOURCE_CODE:      "Source Code",
    CLASS_DOCUMENT:         "Document",
    CLASS_IMAGE:            "Image",
    CLASS_AUDIO:            "Audio",
    CLASS_VIDEO:            "Video",
    CLASS_ARCHIVE:          "Archive",
    CLASS_BINARY:           "Binary",
    CLASS_UNKNOWN:          "Unknown",
}


@dataclass
class FileClassification:
    """
    Represents a file's classification result.

    Attributes:
        relative_path: Path relative to scan root.
        file_class:    One of CLASS_* constants.
        extension:     File extension (lowercase, no leading dot).
        label:         Human-readable class label.
    """
    relative_path: str
    file_class:    str
    extension:     str
    label:         str = ""

    def __post_init__(self):
        if not self.label:
            self.label = CLASS_LABELS.get(self.file_class, "Unknown")
