"""
core/backup.py

Vault backup, restoration, and integrity verification
for the Personal Document Vault.

Backup format:
    A pyzipper AES-encrypted archive containing:
        - database/vault.db
        - vault/encrypted/*.enc
        - backup_manifest.txt

Backup filename format:
    VaultBackup_2025-06-18_14-35-20.pdvbackup
"""

import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pyzipper


# ── Constants ─────────────────────────────────────────────────────────────────

BACKUP_EXTENSION:   str  = ".pdvbackup"
BACKUP_FOLDER:      Path = Path("backups")
DATABASE_PATH:      Path = Path("database") / "vault.db"
VAULT_ENCRYPTED:    Path = Path("vault") / "encrypted"
MANIFEST_FILENAME:  str  = "backup_manifest.txt"
VAULT_VERSION:      str  = "1.0"


# ── Backup creation ───────────────────────────────────────────────────────────

def create_backup(
    password: str,
    destination_folder: Optional[Path] = None
) -> tuple[bool, str]:
    """
    Create a complete encrypted backup of the vault.

    The backup includes the SQLite database and all encrypted
    document files. The archive itself is AES-256 encrypted
    using pyzipper.

    Args:
        password:           The master password used to encrypt the archive.
        destination_folder: Folder to save the backup.
                            Defaults to the backups/ directory.

    Returns:
        A tuple of (success, message).
        On success, message contains the backup file path.
        On failure, message contains the error description.
    """
    if destination_folder is None:
        destination_folder = BACKUP_FOLDER

    destination_folder.mkdir(parents=True, exist_ok=True)

    timestamp   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"VaultBackup_{timestamp}{BACKUP_EXTENSION}"
    backup_path = destination_folder / backup_name

    try:
        with pyzipper.AESZipFile(
            backup_path,
            mode="w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES
        ) as archive:
            archive.setpassword(password.encode("utf-8"))

            # Add database
            if DATABASE_PATH.exists():
                archive.write(DATABASE_PATH, arcname="database/vault.db")

            # Add all encrypted documents
            if VAULT_ENCRYPTED.exists():
                for enc_file in VAULT_ENCRYPTED.glob("*.enc"):
                    archive.write(
                        enc_file,
                        arcname=f"vault/encrypted/{enc_file.name}"
                    )

            # Add manifest
            manifest = _generate_manifest(backup_path)
            archive.writestr(MANIFEST_FILENAME, manifest)

        # Verify the backup immediately after creation
        is_valid, verify_msg = verify_backup(backup_path, password)

        if not is_valid:
            backup_path.unlink(missing_ok=True)
            return False, f"Backup verification failed: {verify_msg}"

        return True, str(backup_path)

    except Exception as error:
        if backup_path.exists():
            backup_path.unlink(missing_ok=True)
        return False, f"Backup failed: {error}"


# ── Backup verification ───────────────────────────────────────────────────────

def verify_backup(
    backup_path: Path,
    password: str
) -> tuple[bool, str]:
    """
    Verify the integrity of a vault backup archive.

    Checks performed:
        - Archive is readable with the given password
        - database/vault.db is present inside the archive
        - Manifest file is present
        - All encrypted files listed are readable

    Args:
        backup_path: Path to the .pdvbackup file.
        password:    The password used to encrypt the backup.

    Returns:
        A tuple of (is_valid, message).
    """
    if not backup_path.exists():
        return False, "Backup file not found."

    try:
        with pyzipper.AESZipFile(backup_path, mode="r") as archive:
            archive.setpassword(password.encode("utf-8"))
            names = archive.namelist()

            if "database/vault.db" not in names:
                return False, "Database missing from backup archive."

            if MANIFEST_FILENAME not in names:
                return False, "Manifest missing from backup archive."

            # Try reading the database bytes to confirm it is not corrupted
            db_bytes = archive.read("database/vault.db")
            if len(db_bytes) < 100:
                return False, "Database inside backup appears corrupted."

        return True, "Backup is valid."

    except RuntimeError:
        return False, "Incorrect backup password."
    except zipfile.BadZipFile:
        return False, "Backup archive is corrupted or not a valid backup."
    except Exception as error:
        return False, f"Verification failed: {error}"


# ── Restore ───────────────────────────────────────────────────────────────────

def restore_backup(
    backup_path: Path,
    password: str
) -> tuple[bool, str]:
    """
    Restore a vault from an encrypted backup archive.

    The restore process:
        1. Verifies the backup is valid and readable.
        2. Extracts contents into a temporary directory.
        3. Replaces the existing database and encrypted files.
        4. Verifies the restored vault is intact.

    If any step fails, the existing vault remains untouched.

    Args:
        backup_path: Path to the .pdvbackup file.
        password:    The password used to encrypt the backup.

    Returns:
        A tuple of (success, message).
    """
    # Step 1 — Verify before touching anything
    is_valid, verify_msg = verify_backup(backup_path, password)
    if not is_valid:
        return False, f"Cannot restore: {verify_msg}"

    # Step 2 — Extract to a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        try:
            with pyzipper.AESZipFile(backup_path, mode="r") as archive:
                archive.setpassword(password.encode("utf-8"))
                archive.extractall(temp_path)
        except Exception as error:
            return False, f"Failed to extract backup: {error}"

        # Step 3 — Validate extracted contents
        restored_db = temp_path / "database" / "vault.db"
        if not restored_db.exists():
            return False, "Restored database not found in extracted archive."

        # Step 4 — Replace database
        try:
            DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(restored_db, DATABASE_PATH)
        except Exception as error:
            return False, f"Failed to restore database: {error}"

        # Step 5 — Replace encrypted files
        restored_vault = temp_path / "vault" / "encrypted"
        if restored_vault.exists():
            try:
                VAULT_ENCRYPTED.mkdir(parents=True, exist_ok=True)
                for enc_file in restored_vault.glob("*.enc"):
                    shutil.copy2(enc_file, VAULT_ENCRYPTED / enc_file.name)
            except Exception as error:
                return False, f"Failed to restore encrypted files: {error}"

    return True, "Vault restored successfully. Please restart the application."


# ── List backups ──────────────────────────────────────────────────────────────

def list_backups(
    folder: Optional[Path] = None
) -> list[Path]:
    """
    Return a list of backup files found in the backup folder.

    Args:
        folder: The folder to search. Defaults to backups/.

    Returns:
        A list of Path objects sorted newest first.
    """
    if folder is None:
        folder = BACKUP_FOLDER

    if not folder.exists():
        return []

    backups = sorted(
        folder.glob(f"*{BACKUP_EXTENSION}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return backups


# ── Manifest ──────────────────────────────────────────────────────────────────

def _generate_manifest(backup_path: Path) -> str:
    """
    Generate a manifest string for the backup archive.

    Args:
        backup_path: The path where the backup will be saved.

    Returns:
        A formatted manifest string.
    """
    enc_count = len(list(VAULT_ENCRYPTED.glob("*.enc"))) if VAULT_ENCRYPTED.exists() else 0
    now       = datetime.now(timezone.utc).isoformat()

    return (
        f"Personal Document Vault Backup\n"
        f"Version: {VAULT_VERSION}\n"
        f"Created: {now}\n"
        f"Documents: {enc_count}\n"
        f"Filename: {backup_path.name}\n"
    )


# ── Vault statistics ──────────────────────────────────────────────────────────

def get_vault_size() -> int:
    """
    Calculate the total size of all encrypted vault files in bytes.

    Returns:
        Total size in bytes.
    """
    if not VAULT_ENCRYPTED.exists():
        return 0
    return sum(f.stat().st_size for f in VAULT_ENCRYPTED.glob("*.enc"))


def get_backup_count() -> int:
    """
    Return the total number of backup files in the backup folder.

    Returns:
        An integer count.
    """
    return len(list_backups())


def get_latest_backup_date() -> Optional[str]:
    """
    Return the creation date of the most recent backup.

    Returns:
        An ISO 8601 date string or None if no backups exist.
    """
    backups = list_backups()
    if not backups:
        return None
    mtime = backups[0].stat().st_mtime
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")



