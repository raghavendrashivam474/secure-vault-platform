"""
modules/password_vault/models/password_category.py

Password Category data model for the Password Vault module.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PasswordCategory:
    """
    Represents a password category.

    Attributes:
        id:             Primary key from the database.
        name:           Display name.
        icon:           Emoji icon character.
        created_at:     ISO 8601 timestamp.
        entry_count:    Number of passwords in this category.
    """

    id:          Optional[int]
    name:        str
    icon:        str = "🔑"
    created_at:  str = ""
    entry_count: int = 0
