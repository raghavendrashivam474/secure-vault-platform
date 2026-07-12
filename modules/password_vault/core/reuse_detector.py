"""
modules/password_vault/core/reuse_detector.py

Password reuse detection using keyed HMAC fingerprints.

Fingerprints exist only in memory during audits.
Never persisted. Never shown to users.
"""

import hmac
import hashlib
from typing import Optional
from modules.password_vault.models.password_entry import PasswordEntry


def compute_fingerprint(password: str, key: bytes) -> str:
    """
    Compute a keyed HMAC fingerprint for password comparison.

    Args:
        password: The plaintext password.
        key:      Session key material.

    Returns:
        A hex string fingerprint.
    """
    return hmac.new(
        key,
        password.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def detect_reused_passwords(
    entries: list[PasswordEntry],
    master_password: str,
    decrypt_fn
) -> dict[str, list[int]]:
    """
    Detect passwords that are reused across multiple entries.

    Args:
        entries:         List of password entries.
        master_password: The session master password (used as key material).
        decrypt_fn:      Callable(encrypted_b64, password) -> plaintext.

    Returns:
        A dict mapping fingerprint to list of entry IDs that share that password.
        Only groups with 2+ entries are returned (actual reuse).
    """
    # Derive key from master password for HMAC
    key = hashlib.sha256(master_password.encode("utf-8")).digest()

    fingerprint_to_ids: dict[str, list[int]] = {}

    for entry in entries:
        try:
            plaintext = decrypt_fn(entry.password_encrypted, master_password)
            if not plaintext:
                continue

            fp = compute_fingerprint(plaintext, key)

            if fp not in fingerprint_to_ids:
                fingerprint_to_ids[fp] = []
            fingerprint_to_ids[fp].append(entry.id)

            # Clear plaintext reference as soon as possible
            plaintext = None

        except Exception:
            continue

    # Only return groups with actual reuse (2+ entries)
    return {
        fp: ids for fp, ids in fingerprint_to_ids.items()
        if len(ids) >= 2
    }


def count_reused_entries(reuse_groups: dict[str, list[int]]) -> int:
    """
    Count total entries involved in reuse.

    Args:
        reuse_groups: Output from detect_reused_passwords().

    Returns:
        Total number of entries with reused passwords.
    """
    return sum(len(ids) for ids in reuse_groups.values())
