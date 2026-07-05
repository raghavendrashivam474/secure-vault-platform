"""
utils/file_utils.py

File handling utilities for the Personal Document Vault.
Updated in Sprint 4 to include filename validation for rename.
"""

import uuid
import re
from pathlib import Path
from typing import Optional


SUPPORTED_EXTENSIONS: set[str] = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

MIME_TYPES: dict[str, str] = {
    ".pdf":  "application/pdf",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

ENCRYPTED_EXTENSION: str    = ".enc"
VAULT_ENCRYPTED_PATH: Path  = Path("vault") / "encrypted"
MAX_DISPLAY_NAME_LENGTH: int = 255

# Characters not allowed in display names
INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def is_supported_file(file_path: Path) -> bool:
    """
    Check whether a file type is supported for import.

    Args:
        file_path: The path to the file.

    Returns:
        True if the extension is supported.
    """
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def is_non_empty_file(file_path: Path) -> bool:
    """
    Check whether a file exists and contains data.

    Args:
        file_path: The path to the file.

    Returns:
        True if the file exists and is larger than zero bytes.
    """
    return file_path.exists() and file_path.stat().st_size > 0


def validate_file(file_path: Path) -> tuple[bool, Optional[str]]:
    """
    Validate a file for import into the vault.

    Args:
        file_path: The path to the file.

    Returns:
        A tuple of (is_valid, error_message).
    """
    if not file_path.exists():
        return False, "File not found."
    if not is_non_empty_file(file_path):
        return False, "File is empty and cannot be imported."
    if not is_supported_file(file_path):
        supported = ", ".join(SUPPORTED_EXTENSIONS)
        return False, f"Unsupported file type. Supported: {supported}"
    return True, None


def validate_display_name(name: str, extension: str) -> tuple[bool, Optional[str]]:
    """
    Validate a proposed display name for a document rename.

    Checks performed:
        - Name is not empty
        - Name does not exceed maximum length
        - Name contains no invalid characters

    Args:
        name:      The proposed display name without extension.
        extension: The file extension to preserve (e.g. '.pdf').

    Returns:
        A tuple of (is_valid, error_message).
    """
    name = name.strip()

    if not name:
        return False, "Name cannot be empty."

    full_name = name + extension

    if len(full_name) > MAX_DISPLAY_NAME_LENGTH:
        return False, f"Name must be {MAX_DISPLAY_NAME_LENGTH} characters or fewer."

    if INVALID_NAME_CHARS.search(name):
        return False, "Name contains invalid characters."

    return True, None


def generate_encrypted_filename() -> str:
    """
    Generate a unique UUID-based filename for an encrypted document.

    Returns:
        A string such as 'c4a7f3d2-8fd0-49ab-b3e1-1234abcd.enc'
    """
    return str(uuid.uuid4()) + ENCRYPTED_EXTENSION


def get_mime_type(file_path: Path) -> str:
    """
    Return the MIME type for a given file.

    Args:
        file_path: The path to the file.

    Returns:
        A MIME type string.
    """
    return MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")


def safe_delete_file(file_path: Path) -> bool:
    """
    Safely delete a file from the filesystem.

    Args:
        file_path: The path to the file to delete.

    Returns:
        True if deleted successfully.
    """
    try:
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception as error:
        print(f"[FileUtils] Failed to delete {file_path}: {error}")
        return False


def ensure_vault_directories() -> None:
    """Ensure all required vault storage directories exist."""
    VAULT_ENCRYPTED_PATH.mkdir(parents=True, exist_ok=True)


