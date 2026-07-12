"""
modules/password_vault/core/vault_import.py

Encrypted Password Vault recovery import.

Reads .pvexport packages and restores password entries
and their history. Validates format version and integrity.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from modules.password_vault.models.password_entry import PasswordEntry
from modules.password_vault.core.database import (
    insert_password, load_all_passwords
)
from modules.password_vault.core.history import add_history_record


SUPPORTED_FORMAT_VERSIONS = ["1.0"]


@dataclass
class RecoveryPreview:
    """
    Preview of recovery import contents.

    Attributes:
        format_version: Package format version.
        module_version: Password Vault version at export.
        exported_at:    Export timestamp.
        entry_count:    Number of entries in package.
        history_count:  Number of history records.
        entries:        Parsed entry dicts.
        history:        Parsed history dicts.
    """
    format_version: str  = ""
    module_version: str  = ""
    exported_at:    str  = ""
    entry_count:    int  = 0
    history_count:  int  = 0
    entries:        list = field(default_factory=list)
    history:        list = field(default_factory=list)


@dataclass
class RecoveryResult:
    """
    Recovery import operation result.

    Attributes:
        success:         True if import succeeded.
        imported:        Number of entries imported.
        duplicates:      Number of duplicates skipped.
        history_added:   Number of history records restored.
        failed:          Number of failures.
        error:           Error message if failed.
    """
    success:       bool  = False
    imported:      int   = 0
    duplicates:    int   = 0
    history_added: int   = 0
    failed:        int   = 0
    error:         str   = ""


def read_package_preview(
    file_path: Path,
    master_password: str
) -> tuple[bool, str, RecoveryPreview]:
    """
    Read and validate a .pvexport package.

    Args:
        file_path:       Path to the export file.
        master_password: Master password for decryption.

    Returns:
        (success, error_message, preview)
    """
    preview = RecoveryPreview()

    try:
        # Read file
        package = file_path.read_bytes()

        if len(package) < 44:
            return False, "Invalid package format.", preview

        # Extract components
        salt       = package[:32]
        nonce      = package[32:44]
        ciphertext = package[44:]

        # Derive key
        key = hashlib.pbkdf2_hmac(
            "sha256",
            master_password.encode("utf-8"),
            salt,
            600_000,
            dklen=32
        )

        # Decrypt
        try:
            aes = AESGCM(key)
            plaintext = aes.decrypt(nonce, ciphertext, None)
        except Exception:
            return False, "Decryption failed. Wrong password or corrupted file.", preview

        # Parse JSON
        try:
            payload = json.loads(plaintext.decode("utf-8"))
        except json.JSONDecodeError:
            return False, "Package payload is corrupted.", preview

        # Validate format
        format_version = payload.get("format_version", "unknown")
        if format_version not in SUPPORTED_FORMAT_VERSIONS:
            return False, f"Unsupported format version: {format_version}", preview

        # Build preview
        preview.format_version = format_version
        preview.module_version = payload.get("module_version", "unknown")
        preview.exported_at    = payload.get("exported_at", "")
        preview.entry_count    = payload.get("entry_count", 0)
        preview.history_count  = payload.get("history_count", 0)
        preview.entries        = payload.get("entries", [])
        preview.history        = payload.get("history", [])

        return True, "", preview

    except Exception as error:
        return False, f"Failed to read package: {error}", preview


def _normalize_website(url) -> str:
    """Normalize a URL for duplicate comparison."""
    if not url:
        return ""
    clean = str(url).lower().strip()
    clean = clean.replace("https://", "").replace("http://", "")
    clean = clean.split("/")[0].replace("www.", "")
    return clean


def restore_package(
    preview: RecoveryPreview,
    skip_duplicates: bool = True
) -> RecoveryResult:
    """
    Restore entries and history from a validated preview.

    Args:
        preview:         The validated recovery preview.
        skip_duplicates: If True, skip entries that match existing entries.

    Returns:
        RecoveryResult with statistics.
    """
    result = RecoveryResult()

    try:
        # Build existing keys for duplicate detection
        existing = load_all_passwords()
        existing_keys = set()
        for e in existing:
            key = (_normalize_website(e.url), e.username.lower().strip())
            existing_keys.add(key)

        # Map old IDs to new IDs for history linking
        id_mapping: dict[int, int] = {}

        # Import entries
        for entry_data in preview.entries:
            try:
                key = (
                    _normalize_website(entry_data.get("url")),
                    entry_data.get("username", "").lower().strip()
                )

                if key in existing_keys and skip_duplicates:
                    result.duplicates += 1
                    continue

                entry = PasswordEntry(
                    id                 = None,
                    title              = entry_data.get("title", ""),
                    username           = entry_data.get("username", ""),
                    password_encrypted = entry_data.get("password_encrypted", ""),
                    url                = entry_data.get("url"),
                    category_id        = entry_data.get("category_id"),
                    notes              = entry_data.get("notes"),
                    is_favorite        = entry_data.get("is_favorite", False),
                    strength_score     = entry_data.get("strength_score", 0)
                )

                new_id = insert_password(entry)
                if new_id is not None:
                    old_id = entry_data.get("id")
                    if old_id is not None:
                        id_mapping[old_id] = new_id
                    result.imported += 1
                else:
                    result.failed += 1

            except Exception:
                result.failed += 1

        # Import history (using ID mapping)
        for history_data in preview.history:
            try:
                old_entry_id = history_data.get("entry_id")
                if old_entry_id not in id_mapping:
                    continue  # Skip history for skipped entries

                new_entry_id = id_mapping[old_entry_id]

                add_history_record(
                    entry_id           = new_entry_id,
                    password_encrypted = history_data.get("password_encrypted", ""),
                    strength_score     = history_data.get("strength_score", 0),
                    reason             = history_data.get("reason", "recovery")
                )
                result.history_added += 1

            except Exception:
                pass

        result.success = True
        return result

    except Exception as error:
        result.success = False
        result.error   = f"Restore failed: {error}"
        return result
