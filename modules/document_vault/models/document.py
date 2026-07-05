"""
models/document.py

Document data model for the Personal Document Vault.
Updated in Sprint 6 to include checksum, expiry,
integrity status, and verification timestamp.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Document:
    """
    Represents a single document stored in the vault.

    Attributes:
        id:                   Primary key from the database.
        uuid:                 Unique identifier used as the encrypted filename.
        original_name:        The display name shown in the dashboard.
        encrypted_name:       The UUID-based filename inside vault/encrypted/.
        file_type:            The file extension (e.g. pdf, png).
        mime_type:            The MIME type (e.g. application/pdf).
        file_size:            File size in bytes.
        date_added:           ISO 8601 timestamp when the document was imported.
        last_modified:        ISO 8601 timestamp of the original file modification.
        notes:                Optional user notes.
        category_id:          Optional category reference.
        is_favorite:          True if the document is marked as a favorite.
        last_opened_at:       ISO 8601 timestamp of the last preview.
        checksum:             SHA-256 checksum of the original plaintext file.
        expiry_date:          ISO date string (YYYY-MM-DD) for document expiry.
        reminder_enabled:     True if expiry reminder is enabled.
        integrity_status:     True if last integrity check passed, False if failed,
                              None if never checked.
        verified_at:          ISO 8601 timestamp of the last integrity verification.
    """

    id:               Optional[int]
    uuid:             str
    original_name:    str
    encrypted_name:   str
    file_type:        str
    mime_type:        str
    file_size:        int
    date_added:       str
    last_modified:    str
    notes:            Optional[str]  = None
    category_id:      Optional[int]  = None
    is_favorite:      bool           = False
    last_opened_at:   Optional[str]  = None
    checksum:         Optional[str]  = None
    expiry_date:      Optional[str]  = None
    reminder_enabled: bool           = False
    integrity_status: Optional[bool] = None
    verified_at:      Optional[str]  = None

    def formatted_size(self) -> str:
        """
        Return the file size as a human-readable string.

        Returns:
            A string such as '1.4 MB' or '340 KB'.
        """
        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 ** 3:
            return f"{size / (1024 ** 2):.1f} MB"
        else:
            return f"{size / (1024 ** 3):.1f} GB"

    def display_name(self) -> str:
        """
        Return the display name without extension.

        Returns:
            A clean display name string.
        """
        from pathlib import Path
        return Path(self.original_name).stem

    def integrity_label(self) -> str:
        """
        Return a human-readable integrity status label.

        Returns:
            A status string for display.
        """
        if self.integrity_status is True:
            return "✓ Verified"
        elif self.integrity_status is False:
            return "⚠ Failed"
        else:
            return "— Not checked"

