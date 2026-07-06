"""
vaultcore/storage_index.py

Storage Index for the Secure Vault Platform.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from vaultcore.logger import log_error


DATABASE_PATH: Path = Path("database") / "vault.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_storage_index() -> None:
    """Create the storage_index table if it does not exist."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS storage_index (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id       TEXT    NOT NULL UNIQUE,
                module_id     TEXT    NOT NULL,
                relative_path TEXT    NOT NULL,
                storage_path  TEXT    NOT NULL,
                file_size     INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT    NOT NULL,
                modified_at   TEXT,
                checksum      TEXT
            )
        """)
        connection.commit()
    finally:
        connection.close()


def index_file(
    file_id: str,
    module_id: str,
    relative_path: str,
    storage_path: str,
    file_size: int,
    checksum: Optional[str] = None
) -> bool:
    """Add or update a file entry in the storage index."""
    connection = get_connection()
    try:
        now    = datetime.now(timezone.utc).isoformat()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO storage_index
                (file_id, module_id, relative_path, storage_path,
                 file_size, created_at, modified_at, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_id) DO UPDATE SET
                file_size   = excluded.file_size,
                modified_at = excluded.modified_at,
                checksum    = excluded.checksum
        """, (
            file_id, module_id, relative_path,
            storage_path, file_size, now, now, checksum
        ))
        connection.commit()
        return True
    except Exception as error:
        log_error(f"[StorageIndex] Index failed: {error}")
        return False
    finally:
        connection.close()


def remove_from_index(file_id: str) -> bool:
    """Remove a file entry from the storage index."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM storage_index WHERE file_id = ?", (file_id,)
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception as error:
        log_error(f"[StorageIndex] Remove failed: {error}")
        return False
    finally:
        connection.close()


def get_module_storage_size(module_id: str) -> int:
    """Return total indexed storage size for a module in bytes."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT SUM(file_size) FROM storage_index WHERE module_id = ?",
            (module_id,)
        )
        result = cursor.fetchone()[0]
        return result or 0
    except Exception:
        return 0
    finally:
        connection.close()


def get_total_indexed_size() -> int:
    """Return total size of all indexed files in bytes."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT SUM(file_size) FROM storage_index")
        result = cursor.fetchone()[0]
        return result or 0
    except Exception:
        return 0
    finally:
        connection.close()


def get_file_count(module_id: Optional[str] = None) -> int:
    """Return number of indexed files."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        if module_id:
            cursor.execute(
                "SELECT COUNT(*) FROM storage_index WHERE module_id = ?",
                (module_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM storage_index")
        return cursor.fetchone()[0]
    except Exception:
        return 0
    finally:
        connection.close()
