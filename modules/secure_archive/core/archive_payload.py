"""
modules/secure_archive/core/archive_payload.py

Builds ArchivePayload from manifest and compressed entries.
"""

from modules.secure_archive.models.manifest import ArchiveManifest
from modules.secure_archive.models.archive_payload import (
    ArchivePayload, PAYLOAD_VERSION
)


class ArchivePayloadBuilder:
    """
    Builds an ArchivePayload combining manifest and compressed data.

    Encryption operates on the payload as a whole.
    """

    def build(
        self,
        manifest: ArchiveManifest,
        compressed_entries: dict[str, bytes],
        metadata: dict = None
    ) -> ArchivePayload:
        """
        Build the archive payload.

        Args:
            manifest:           The archive manifest.
            compressed_entries: Dict mapping relative_path -> compressed bytes.
            metadata:           Optional extra metadata.

        Returns:
            An ArchivePayload ready for encryption.
        """
        return ArchivePayload(
            payload_version    = PAYLOAD_VERSION,
            manifest           = manifest,
            compressed_entries = compressed_entries,
            metadata           = metadata or {}
        )
