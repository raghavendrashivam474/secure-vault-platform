"""
modules/secure_archive/models/manifest.py

Archive Manifest v1 data models.

The manifest is the blueprint required for restoration.
It describes what was archived and how.
"""

import uuid
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone


# Current manifest format version
MANIFEST_FORMAT_VERSION = 1


@dataclass
class ManifestFileEntry:
    """
    Represents one file inside the archive manifest.

    Attributes:
        path:                  Relative path inside archive (forward slashes).
        original_size:         Size before compression.
        compressed_size:       Size after compression.
        checksum:              SHA-256 of original file contents.
        file_class:            File classification.
        compression_strategy:  Strategy used.
        compression_level:     Numeric level (0-9).
    """
    path:                  str
    original_size:         int
    compressed_size:       int
    checksum:              str
    file_class:            str
    compression_strategy:  str
    compression_level:     int


@dataclass
class ArchiveManifest:
    """
    Complete archive manifest.

    Attributes:
        format_version:   Manifest schema version (integer).
        archive_id:       Unique identifier (UUID).
        archive_name:     Original archive name.
        module_version:   Secure Archive version that created this.
        project_type:     Detected project type.
        project_confidence: Detection confidence level.
        created_at:       ISO 8601 timestamp.
        file_count:       Total files in archive.
        original_size:    Sum of original file sizes.
        compressed_size:  Sum of compressed sizes.
        files:            List of file entries.
    """
    format_version:      int
    archive_id:          str
    archive_name:        str
    module_version:      str
    project_type:        str
    project_confidence:  str
    created_at:          str
    file_count:          int
    original_size:       int
    compressed_size:     int
    files:               list[ManifestFileEntry] = field(default_factory=list)

    # Manifest v2 additions (Sprint 16)
    archive_root:        str         = ""
    original_source_path: str        = ""
    directory_paths:     list[str]   = field(default_factory=list)
    empty_directory_count: int       = 0

    # Manifest v2 additions (Sprint 16)
    archive_root:        str         = ""
    original_source_path: str        = ""
    directory_paths:     list[str]   = field(default_factory=list)
    empty_directory_count: int       = 0

    # Manifest v2 additions (Sprint 16)
    archive_root:        str         = ""
    original_source_path: str        = ""
    directory_paths:     list[str]   = field(default_factory=list)
    empty_directory_count: int       = 0

    def to_json(self) -> str:
        """Serialize manifest to JSON string."""
        data = {
            "format_version":     self.format_version,
            "archive_id":         self.archive_id,
            "archive_name":       self.archive_name,
            "module_version":     self.module_version,
            "project_type":       self.project_type,
            "project_confidence": self.project_confidence,
            "created_at":         self.created_at,
            "file_count":         self.file_count,
            "original_size":      self.original_size,
            "compressed_size":    self.compressed_size,
            "archive_root":         self.archive_root,
            "original_source_path": self.original_source_path,
            "directory_paths":      self.directory_paths,
            "empty_directory_count": self.empty_directory_count,
            "archive_root":         self.archive_root,
            "original_source_path": self.original_source_path,
            "directory_paths":      self.directory_paths,
            "empty_directory_count": self.empty_directory_count,
            "archive_root":         self.archive_root,
            "original_source_path": self.original_source_path,
            "directory_paths":      self.directory_paths,
            "empty_directory_count": self.empty_directory_count,
            "files": [
                {
                    "path":                 f.path,
                    "original_size":        f.original_size,
                    "compressed_size":      f.compressed_size,
                    "checksum":             f.checksum,
                    "file_class":           f.file_class,
                    "compression_strategy": f.compression_strategy,
                    "compression_level":    f.compression_level,
                }
                for f in self.files
            ]
        }
        return json.dumps(data, indent=2)

    def to_bytes(self) -> bytes:
        """Serialize to UTF-8 bytes."""
        return self.to_json().encode("utf-8")

    @classmethod
    def from_json(cls, json_str: str) -> "ArchiveManifest":
        """
        Deserialize manifest from JSON string.

        Raises:
            ValueError: If format version is unsupported.
        """
        data = json.loads(json_str)

        format_version = data.get("format_version")
        if format_version != MANIFEST_FORMAT_VERSION:
            raise ValueError(
                f"Unsupported manifest format version: {format_version} "
                f"(expected {MANIFEST_FORMAT_VERSION})"
            )

        files = [
            ManifestFileEntry(
                path                 = f["path"],
                original_size        = f["original_size"],
                compressed_size      = f["compressed_size"],
                checksum             = f["checksum"],
                file_class           = f["file_class"],
                compression_strategy = f["compression_strategy"],
                compression_level    = f["compression_level"],
            )
            for f in data.get("files", [])
        ]

        return cls(
            format_version     = format_version,
            archive_id         = data["archive_id"],
            archive_name       = data["archive_name"],
            module_version     = data["module_version"],
            project_type       = data["project_type"],
            project_confidence = data["project_confidence"],
            created_at         = data["created_at"],
            file_count         = data["file_count"],
            original_size      = data["original_size"],
            compressed_size    = data["compressed_size"],
            files              = files,
            archive_root       = data.get("archive_root", ""),
            original_source_path = data.get("original_source_path", ""),
            directory_paths    = data.get("directory_paths", []),
            empty_directory_count = data.get("empty_directory_count", 0),
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "ArchiveManifest":
        """Deserialize from UTF-8 bytes."""
        return cls.from_json(data.decode("utf-8"))


