"""
modules/password_vault/models/password_entry.py

Password Entry data model for the Password Vault module.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PasswordEntry:
    """
    Represents a single password entry in the Password Vault.

    Attributes:
        id:                 Primary key from the database.
        title:              Display name of the entry.
        username:           Username or email.
        password_encrypted: The encrypted password bytes.
        url:                Optional website URL.
        category_id:        Optional category reference.
        notes:              Optional user notes.
        is_favorite:        True if marked as favorite.
        strength_score:     Password strength (0-100).
        created_at:         ISO 8601 creation timestamp.
        modified_at:        ISO 8601 modification timestamp.
        last_accessed:      ISO 8601 last accessed timestamp.
    """

    id:                 Optional[int]
    title:              str
    username:           str
    password_encrypted: str
    url:                Optional[str] = None
    category_id:        Optional[int] = None
    notes:              Optional[str] = None
    is_favorite:        bool          = False
    strength_score:     int           = 0
    created_at:         str           = ""
    modified_at:        str           = ""
    last_accessed:      Optional[str] = None
    password_changed_at: Optional[str] = None

    def display_url(self) -> str:
        """Return a shortened URL for display."""
        if not self.url:
            return ""
        url = self.url.replace("https://", "").replace("http://", "")
        url = url.split("/")[0]
        return url if len(url) < 40 else url[:40] + "..."

    def strength_label(self) -> str:
        """Return a human-readable strength label."""
        if self.strength_score >= 80:
            return "Very Strong"
        elif self.strength_score >= 60:
            return "Strong"
        elif self.strength_score >= 40:
            return "Fair"
        else:
            return "Weak"

