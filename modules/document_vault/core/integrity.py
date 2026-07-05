"""
core/integrity.py

Document integrity verification for the Personal Document Vault.
Handles SHA-256 checksum generation, storage, and verification.
Also provides vault-wide health check functionality.
"""

import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from vaultcore.file_utils import VAULT_ENCRYPTED_PATH


CHECKSUM_ALGORITHM: str = "sha256"


# ── Checksum generation ───────────────────────────────────────────────────────

def generate_checksum(file_path: Path) -> Optional[str]:
    """
    Generate a SHA-256 checksum of a file's contents.

    The checksum is computed on the plaintext file
    before encryption during import.

    Args:
        file_path: Path to the file to checksum.

    Returns:
        A hex string SHA-256 checksum, or None if the file
        cannot be read.
    """
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as error:
        print(f"[Integrity] Checksum generation failed: {error}")
        return None


def generate_encrypted_checksum(encrypted_path: Path) -> Optional[str]:
    """
    Generate a SHA-256 checksum of an encrypted file.

    Used to verify that the encrypted file has not been
    tampered with or corrupted after storage.

    Args:
        encrypted_path: Path to the .enc file.

    Returns:
        A hex string SHA-256 checksum, or None on failure.
    """
    return generate_checksum(encrypted_path)


# ── Integrity verification ────────────────────────────────────────────────────

def verify_document_integrity(
    encrypted_name: str,
    stored_checksum: Optional[str],
    master_password: str
) -> tuple[bool, str]:
    """
    Verify the integrity of a stored encrypted document.

    Decrypts the document in memory and compares its
    checksum against the stored value.

    Args:
        encrypted_name:   The UUID filename of the encrypted file.
        stored_checksum:  The SHA-256 checksum stored at import time.
        master_password:  The master password for decryption.

    Returns:
        A tuple of (is_valid, message).
    """
    encrypted_path = VAULT_ENCRYPTED_PATH / encrypted_name

    if not encrypted_path.exists():
        return False, "Encrypted file missing from vault storage."

    if stored_checksum is None:
        return False, "No checksum stored for this document."

    try:
        from vaultcore.encryption import decrypt_file_to_memory
        decrypted_bytes = decrypt_file_to_memory(encrypted_path, master_password)

        if decrypted_bytes is None:
            return False, "Decryption failed. File may be corrupted."

        hasher = hashlib.sha256()
        hasher.update(decrypted_bytes)
        computed = hasher.hexdigest()

        if computed == stored_checksum:
            return True, "Integrity verified. Document is intact."
        else:
            return False, "Checksum mismatch. Document may be corrupted."

    except Exception as error:
        return False, f"Verification error: {error}"


# ── Vault health check ────────────────────────────────────────────────────────

def run_vault_health_check(master_password: str) -> dict:
    """
    Perform a complete vault health scan.

    Checks performed:
        - Missing encrypted files (in DB but not on disk)
        - Orphaned encrypted files (on disk but not in DB)
        - Duplicate checksums in the database
        - Files that fail integrity verification

    Args:
        master_password: The master password for decryption checks.

    Returns:
        A dictionary containing health check results.
    """
    from vaultcore.database import load_all_documents

    documents       = load_all_documents()
    db_filenames    = {d.encrypted_name for d in documents}
    disk_files      = set()

    if VAULT_ENCRYPTED_PATH.exists():
        disk_files = {f.name for f in VAULT_ENCRYPTED_PATH.glob("*.enc")}

    missing_files   = []
    orphaned_files  = []
    integrity_fails = []
    duplicate_checksums = []

    # Check for missing files
    for doc in documents:
        if doc.encrypted_name not in disk_files:
            missing_files.append(doc.original_name)

    # Check for orphaned files
    for filename in disk_files:
        if filename not in db_filenames:
            orphaned_files.append(filename)

    # Check for duplicate checksums
    checksums = {}
    for doc in documents:
        if doc.checksum:
            if doc.checksum in checksums:
                duplicate_checksums.append({
                    "original": checksums[doc.checksum],
                    "duplicate": doc.original_name
                })
            else:
                checksums[doc.checksum] = doc.original_name

    # Check integrity of each document
    for doc in documents:
        if doc.encrypted_name in disk_files and doc.checksum:
            is_valid, message = verify_document_integrity(
                doc.encrypted_name,
                doc.checksum,
                master_password
            )
            if not is_valid:
                integrity_fails.append({
                    "name":    doc.original_name,
                    "reason":  message
                })

    total = len(documents)
    healthy = total - len(missing_files) - len(integrity_fails)

    return {
        "total_documents":    total,
        "healthy_documents":  max(healthy, 0),
        "missing_files":      missing_files,
        "orphaned_files":     orphaned_files,
        "integrity_failures": integrity_fails,
        "duplicate_checksums": duplicate_checksums,
        "scan_time":          datetime.now(timezone.utc).isoformat(),
        "vault_healthy":      (
            len(missing_files) == 0
            and len(integrity_fails) == 0
            and len(orphaned_files) == 0
        )
    }

