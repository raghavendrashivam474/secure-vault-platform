"""
modules/password_vault/models/password_history.py

Password History record model.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PasswordHistoryRecord:
    """
    Represents a single historical password version.

    Attributes:
        id:                 Primary key.
        entry_id:           Reference to PasswordEntry.
        password_encrypted: Encrypted historical password (base64).
        strength_score:     Strength at time of storage.
        changed_at:         ISO 8601 timestamp when replaced.
        reason:             Optional reason ('user_edit', 'restore').
    """
    id:                 Optional[int]
    entry_id:           int
    password_encrypted: str
    strength_score:     int
    changed_at:         str
    reason:             str = "user_edit"
