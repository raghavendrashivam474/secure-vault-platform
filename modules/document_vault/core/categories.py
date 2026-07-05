"""
core/categories.py

Category management for the Personal Document Vault.
Handles creation, renaming, deletion, and assignment of categories.
All database operations are delegated to core/database.py.
"""

from typing import Optional
from modules.document_vault.models.category import Category


# Maximum allowed length for a category name
MAX_CATEGORY_NAME_LENGTH: int = 64

# Default categories created on first launch
DEFAULT_CATEGORIES: list[str] = [
    "Identity",
    "Education",
    "Medical",
    "Banking",
    "Insurance",
    "Property",
    "Personal",
]


def validate_category_name(
    name: str,
    existing_names: list[str],
    current_name: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate a category name before creation or rename.

    Args:
        name:          The proposed category name.
        existing_names: All current category names in the database.
        current_name:  The current name if renaming (excluded from duplicate check).

    Returns:
        A tuple of (is_valid, error_message).
        If valid, error_message is None.
    """
    name = name.strip()

    if not name:
        return False, "Category name cannot be empty."

    if len(name) > MAX_CATEGORY_NAME_LENGTH:
        return False, f"Category name must be {MAX_CATEGORY_NAME_LENGTH} characters or fewer."

    duplicates = [n.lower() for n in existing_names]

    if current_name:
        duplicates = [n for n in duplicates if n != current_name.lower()]

    if name.lower() in duplicates:
        return False, f"A category named '{name}' already exists."

    return True, None


def get_default_categories() -> list[str]:
    """
    Return the list of default category names.

    Returns:
        A list of default category name strings.
    """
    return DEFAULT_CATEGORIES.copy()

