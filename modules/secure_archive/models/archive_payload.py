"""
modules/secure_archive/models/archive_payload.py

Archive Payload data model.

Combines the manifest and compressed entries into one
serializable container that the encryption layer operates on.

The payload knows nothing about encryption or compression.
It is simply a portable container.
"""

import json
import struct
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

from modules.secure_archive.models.manifest import ArchiveManifest


# Payload format version
PAYLOAD_VERSION = 1


@dataclass
class ArchivePayload:
    """
    Complete archive payload combining manifest and compressed entries.

    Attributes:
        payload_version:      Payload schema version.
        manifest:             The archive manifest.
        compressed_entries:   Dict mapping relative_path -> compressed bytes.
        metadata:             Optional extra metadata (dict).
        created_at:           ISO 8601 timestamp.
    """
    payload_version:    int
    manifest:           ArchiveManifest
    compressed_entries: dict[str, bytes]      = field(default_factory=dict)
    metadata:           dict                  = field(default_factory=dict)
    created_at:         str                   = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def entry_count(self) -> int:
        """Number of compressed entries in payload."""
        return len(self.compressed_entries)

    @property
    def total_compressed_size(self) -> int:
        """Total bytes of all compressed entries."""
        return sum(len(data) for data in self.compressed_entries.values())

    def to_bytes(self) -> bytes:
        """
        Serialize payload to bytes.

        Layout:
            [4 bytes] payload_version (uint32 big-endian)
            [4 bytes] manifest length (uint32 big-endian)
            [N bytes] manifest JSON (UTF-8)
            [4 bytes] metadata length (uint32 big-endian)
            [N bytes] metadata JSON (UTF-8)
            [4 bytes] entry count (uint32 big-endian)
            For each entry:
                [4 bytes] path length (uint32 big-endian)
                [N bytes] path (UTF-8)
                [8 bytes] data length (uint64 big-endian)
                [N bytes] compressed data
        """
        parts = []

        # Payload version
        parts.append(struct.pack(">I", self.payload_version))

        # Manifest
        manifest_bytes = self.manifest.to_bytes()
        parts.append(struct.pack(">I", len(manifest_bytes)))
        parts.append(manifest_bytes)

        # Metadata
        metadata_bytes = json.dumps(self.metadata).encode("utf-8")
        parts.append(struct.pack(">I", len(metadata_bytes)))
        parts.append(metadata_bytes)

        # Entry count
        parts.append(struct.pack(">I", len(self.compressed_entries)))

        # Entries in manifest order (deterministic)
        for entry in self.manifest.files:
            path       = entry.path
            path_bytes = path.encode("utf-8")
            data       = self.compressed_entries.get(path, b"")

            parts.append(struct.pack(">I", len(path_bytes)))
            parts.append(path_bytes)
            parts.append(struct.pack(">Q", len(data)))
            parts.append(data)

        return b"".join(parts)

    @classmethod
    def from_bytes(cls, data: bytes) -> "ArchivePayload":
        """
        Deserialize payload from bytes.

        Raises:
            ValueError: If payload version is unsupported or data is malformed.
        """
        offset = 0

        # Payload version
        if len(data) < 4:
            raise ValueError("Payload too small for version header")
        payload_version = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4

        if payload_version != PAYLOAD_VERSION:
            raise ValueError(
                f"Unsupported payload version: {payload_version} "
                f"(expected {PAYLOAD_VERSION})"
            )

        # Manifest
        if len(data) < offset + 4:
            raise ValueError("Payload truncated at manifest length")
        manifest_length = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4

        if len(data) < offset + manifest_length:
            raise ValueError("Payload truncated at manifest data")
        manifest_bytes = data[offset:offset+manifest_length]
        offset += manifest_length

        manifest = ArchiveManifest.from_bytes(manifest_bytes)

        # Metadata
        if len(data) < offset + 4:
            raise ValueError("Payload truncated at metadata length")
        metadata_length = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4

        if len(data) < offset + metadata_length:
            raise ValueError("Payload truncated at metadata")
        metadata_bytes = data[offset:offset+metadata_length]
        offset += metadata_length

        metadata = json.loads(metadata_bytes.decode("utf-8")) if metadata_bytes else {}

        # Entry count
        if len(data) < offset + 4:
            raise ValueError("Payload truncated at entry count")
        entry_count = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4

        # Entries
        entries = {}
        for _ in range(entry_count):
            if len(data) < offset + 4:
                raise ValueError("Payload truncated at entry path length")
            path_length = struct.unpack(">I", data[offset:offset+4])[0]
            offset += 4

            if len(data) < offset + path_length:
                raise ValueError("Payload truncated at entry path")
            path = data[offset:offset+path_length].decode("utf-8")
            offset += path_length

            if len(data) < offset + 8:
                raise ValueError("Payload truncated at entry data length")
            data_length = struct.unpack(">Q", data[offset:offset+8])[0]
            offset += 8

            if len(data) < offset + data_length:
                raise ValueError("Payload truncated at entry data")
            entry_data = data[offset:offset+data_length]
            offset += data_length

            entries[path] = entry_data

        return cls(
            payload_version    = payload_version,
            manifest           = manifest,
            compressed_entries = entries,
            metadata           = metadata,
        )
