"""
models/category.py

Category data model for the Personal Document Vault.
Represents a single document category.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    """
    Represents a document category inside the vault.

    Attributes:
        id:            Primary key from the database.
        name:          Display name of the category.
        description:   Optional description. Reserved for future use.
        created_at:    ISO 8601 timestamp when the category was created.
        document_count: Number of documents in this category.
                        Populated at query time, not stored in database.
    """

    id:             Optional[int]
    name:           str
    description:    Optional[str]
    created_at:     str
    document_count: int = 0

