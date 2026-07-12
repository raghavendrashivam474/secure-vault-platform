"""
modules/password_vault/core/vault_export.py

Encrypted Password Vault export.

Creates a versioned encrypted package containing all
password entries and their history. Default format is
always encrypted, never plaintext.

Package format:
    Salt (32 bytes) + Nonce (12 bytes) + Ciphertext
Where ciphertext = AES-256-GCM(JSON payload)

JSON payload:
    {
      "format_version": "1.0",
      "module_version": "1.0.0",
      "exported_at":    ISO timestamp,
      "entry_count":    int,
      "entries":        [{...}],
      "history":        [{...}]
    }
"""

import os
import json
import base64
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from modules.password_vault.core.database import load_all_passwords
from modules.password_vault.core.history import get_history_for_entry


EXPORT_FORMAT_VERSION = "1.0"
EXPORT_MODULE_VERSION = "1.0.0"
EXPORT_EXTENSION      = ".pvexport"


@dataclass
class ExportResult:
    """
    Export operation result.

    Attributes:
        success:       True if export succeeded.
        file_path:     Path to created export file.
        entry_count:   Number of entries exported.
        history_count: Number of history records exported.
        error:         Error message if failed.
    """
    success:       bool
    file_path:     str = ""
    entry_count:   int = 0
    history_count: int = 0
    error:         str = ""


def export_vault(
    destination_folder: Path,
    master_password: str
) -> ExportResult:
    """
    Export the entire Password Vault to an encrypted package.

    Args:
        destination_folder: Where to save the export.
        master_password:    Master password for encryption.

    Returns:
        ExportResult with details.
    """
    try:
        # Load all data
        entries       = load_all_passwords()
        entry_dicts   = []
        history_dicts = []

        for entry in entries:
            entry_dicts.append({
                "id":                  entry.id,
                "title":               entry.title,
                "username":            entry.username,
                "password_encrypted":  entry.password_encrypted,
                "url":                 entry.url,
                "category_id":         entry.category_id,
                "notes":               entry.notes,
                "is_favorite":         entry.is_favorite,
                "strength_score":      entry.strength_score,
                "created_at":          entry.created_at,
                "modified_at":         entry.modified_at,
                "last_accessed":       entry.last_accessed,
                "password_changed_at": getattr(entry, "password_changed_at", entry.modified_at),
            })

            # Include history
            history = get_history_for_entry(entry.id)
            for record in history:
                history_dicts.append({
                    "id":                  record.id,
                    "entry_id":            record.entry_id,
                    "password_encrypted":  record.password_encrypted,
                    "strength_score":      record.strength_score,
                    "changed_at":          record.changed_at,
                    "reason":              record.reason,
                })

        # Build manifest
        payload = {
            "format_version": EXPORT_FORMAT_VERSION,
            "module_version": EXPORT_MODULE_VERSION,
            "exported_at":    datetime.now(timezone.utc).isoformat(),
            "entry_count":    len(entry_dicts),
            "history_count":  len(history_dicts),
            "entries":        entry_dicts,
            "history":        history_dicts,
        }

        # Serialize
        json_bytes = json.dumps(payload, indent=None).encode("utf-8")

        # Encrypt
        salt  = os.urandom(32)
        nonce = os.urandom(12)
        key   = hashlib.pbkdf2_hmac(
            "sha256",
            master_password.encode("utf-8"),
            salt,
            600_000,
            dklen=32
        )
        aes = AESGCM(key)
        ciphertext = aes.encrypt(nonce, json_bytes, None)

        # Package: salt + nonce + ciphertext
        package = salt + nonce + ciphertext

        # Write file
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename  = f"PasswordVaultExport_{timestamp}{EXPORT_EXTENSION}"

        destination_folder.mkdir(parents=True, exist_ok=True)
        output_path = destination_folder / filename
        output_path.write_bytes(package)

        return ExportResult(
            success       = True,
            file_path     = str(output_path),
            entry_count   = len(entry_dicts),
            history_count = len(history_dicts)
        )

    except Exception as error:
        return ExportResult(
            success = False,
            error   = f"Export failed: {error}"
        )
