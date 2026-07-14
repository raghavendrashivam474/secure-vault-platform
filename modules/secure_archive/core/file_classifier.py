"""
modules/secure_archive/core/file_classifier.py

Extension-based file classifier.

Classifies files by type category. Compression decisions
happen elsewhere — this only categorizes files.
"""

from modules.secure_archive.models.scan import ScannedFile
from modules.secure_archive.models.classification import (
    FileClassification,
    CLASS_TEXT, CLASS_STRUCTURED_TEXT, CLASS_SOURCE_CODE,
    CLASS_DOCUMENT, CLASS_IMAGE, CLASS_AUDIO, CLASS_VIDEO,
    CLASS_ARCHIVE, CLASS_BINARY, CLASS_UNKNOWN
)


# Extension to class mapping
EXTENSION_MAP = {
    # Source Code
    "py":   CLASS_SOURCE_CODE,
    "js":   CLASS_SOURCE_CODE,
    "ts":   CLASS_SOURCE_CODE,
    "tsx":  CLASS_SOURCE_CODE,
    "jsx":  CLASS_SOURCE_CODE,
    "java": CLASS_SOURCE_CODE,
    "c":    CLASS_SOURCE_CODE,
    "cpp":  CLASS_SOURCE_CODE,
    "h":    CLASS_SOURCE_CODE,
    "hpp":  CLASS_SOURCE_CODE,
    "cs":   CLASS_SOURCE_CODE,
    "rs":   CLASS_SOURCE_CODE,
    "go":   CLASS_SOURCE_CODE,
    "dart": CLASS_SOURCE_CODE,
    "rb":   CLASS_SOURCE_CODE,
    "php":  CLASS_SOURCE_CODE,
    "swift":CLASS_SOURCE_CODE,
    "kt":   CLASS_SOURCE_CODE,
    "scala":CLASS_SOURCE_CODE,
    "sh":   CLASS_SOURCE_CODE,
    "bash": CLASS_SOURCE_CODE,
    "ps1":  CLASS_SOURCE_CODE,
    "sql":  CLASS_SOURCE_CODE,
    "html": CLASS_SOURCE_CODE,
    "css":  CLASS_SOURCE_CODE,
    "scss": CLASS_SOURCE_CODE,
    "vue":  CLASS_SOURCE_CODE,

    # Structured Text
    "json": CLASS_STRUCTURED_TEXT,
    "xml":  CLASS_STRUCTURED_TEXT,
    "yaml": CLASS_STRUCTURED_TEXT,
    "yml":  CLASS_STRUCTURED_TEXT,
    "toml": CLASS_STRUCTURED_TEXT,
    "csv":  CLASS_STRUCTURED_TEXT,
    "tsv":  CLASS_STRUCTURED_TEXT,
    "ini":  CLASS_STRUCTURED_TEXT,
    "cfg":  CLASS_STRUCTURED_TEXT,
    "conf": CLASS_STRUCTURED_TEXT,

    # Text
    "md":       CLASS_TEXT,
    "markdown": CLASS_TEXT,
    "txt":      CLASS_TEXT,
    "log":      CLASS_TEXT,
    "rst":      CLASS_TEXT,
    "readme":   CLASS_TEXT,

    # Documents
    "pdf":  CLASS_DOCUMENT,
    "doc":  CLASS_DOCUMENT,
    "docx": CLASS_DOCUMENT,
    "odt":  CLASS_DOCUMENT,
    "rtf":  CLASS_DOCUMENT,
    "xls":  CLASS_DOCUMENT,
    "xlsx": CLASS_DOCUMENT,
    "ods":  CLASS_DOCUMENT,
    "ppt":  CLASS_DOCUMENT,
    "pptx": CLASS_DOCUMENT,
    "odp":  CLASS_DOCUMENT,

    # Images (already compressed)
    "jpg":  CLASS_IMAGE,
    "jpeg": CLASS_IMAGE,
    "png":  CLASS_IMAGE,
    "gif":  CLASS_IMAGE,
    "webp": CLASS_IMAGE,
    "bmp":  CLASS_IMAGE,
    "svg":  CLASS_IMAGE,
    "ico":  CLASS_IMAGE,
    "tiff": CLASS_IMAGE,
    "tif":  CLASS_IMAGE,
    "heic": CLASS_IMAGE,

    # Audio (already compressed)
    "mp3":  CLASS_AUDIO,
    "wav":  CLASS_AUDIO,
    "flac": CLASS_AUDIO,
    "aac":  CLASS_AUDIO,
    "ogg":  CLASS_AUDIO,
    "m4a":  CLASS_AUDIO,
    "wma":  CLASS_AUDIO,

    # Video (already compressed)
    "mp4":  CLASS_VIDEO,
    "mkv":  CLASS_VIDEO,
    "avi":  CLASS_VIDEO,
    "mov":  CLASS_VIDEO,
    "wmv":  CLASS_VIDEO,
    "flv":  CLASS_VIDEO,
    "webm": CLASS_VIDEO,
    "m4v":  CLASS_VIDEO,

    # Archives (already compressed)
    "zip":  CLASS_ARCHIVE,
    "rar":  CLASS_ARCHIVE,
    "7z":   CLASS_ARCHIVE,
    "tar":  CLASS_ARCHIVE,
    "gz":   CLASS_ARCHIVE,
    "bz2":  CLASS_ARCHIVE,
    "xz":   CLASS_ARCHIVE,
    "zst":  CLASS_ARCHIVE,

    # Binary
    "exe":  CLASS_BINARY,
    "dll":  CLASS_BINARY,
    "so":   CLASS_BINARY,
    "dylib":CLASS_BINARY,
    "bin":  CLASS_BINARY,
    "obj":  CLASS_BINARY,
    "o":    CLASS_BINARY,
    "a":    CLASS_BINARY,
    "lib":  CLASS_BINARY,
    "pyd":  CLASS_BINARY,
    "class":CLASS_BINARY,
    "jar":  CLASS_BINARY,
    "war":  CLASS_BINARY,
    "apk":  CLASS_BINARY,
    "ipa":  CLASS_BINARY,
    "deb":  CLASS_BINARY,
    "rpm":  CLASS_BINARY,
    "msi":  CLASS_BINARY,
    "dmg":  CLASS_BINARY,
    "iso":  CLASS_BINARY,
}


class FileClassifier:
    """
    Classifies files by extension into type categories.

    Does not make compression decisions.
    Does not read file contents.
    """

    def classify(self, file_entry: ScannedFile) -> FileClassification:
        """
        Classify a single file.

        Args:
            file_entry: The scanned file.

        Returns:
            A FileClassification.
        """
        extension = file_entry.extension.lower()
        file_class = EXTENSION_MAP.get(extension, CLASS_UNKNOWN)

        return FileClassification(
            relative_path = file_entry.relative_path,
            file_class    = file_class,
            extension     = extension
        )

    def classify_all(
        self,
        files: list[ScannedFile]
    ) -> list[FileClassification]:
        """
        Classify a list of scanned files.

        Args:
            files: List of scanned files.

        Returns:
            List of classifications in same order.
        """
        return [self.classify(f) for f in files]

    def summarize(
        self,
        classifications: list[FileClassification]
    ) -> dict[str, int]:
        """
        Count classifications by class.

        Args:
            classifications: List of classifications.

        Returns:
            Dictionary mapping class name to count.
        """
        counts = {}
        for c in classifications:
            counts[c.file_class] = counts.get(c.file_class, 0) + 1
        return counts
