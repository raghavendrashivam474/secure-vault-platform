"""
modules/password_vault/core/history.py

Password History repository and version management.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from modules.password_vault.models.password_history import PasswordHistoryRecord


DATABASE_PATH: Path = Path("database") / "vault.db"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_history_table() -> None:
    """Create the password_history table if missing."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_history (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id           INTEGER NOT NULL,
                password_encrypted TEXT    NOT NULL,
                strength_score     INTEGER NOT NULL DEFAULT 0,
                changed_at         TEXT    NOT NULL,
                reason             TEXT    NOT NULL DEFAULT 'user_edit',
                FOREIGN KEY (entry_id) REFERENCES password_entries(id) ON DELETE CASCADE
            )
        """)
        connection.commit()
    finally:
        connection.close()


def add_history_record(
    entry_id: int,
    password_encrypted: str,
    strength_score: int,
    reason: str = "user_edit"
) -> Optional[int]:
    """
    Add a new history record when a password is replaced.

    Args:
        entry_id:           The password entry ID.
        password_encrypted: The previous encrypted password.
        strength_score:     Strength of the previous password.
        reason:             'user_edit' or 'restore'.

    Returns:
        The new history record ID or None on failure.
    """
    connection = _connect()
    try:
        cursor = connection.cursor()
        now    = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO password_history
                (entry_id, password_encrypted, strength_score, changed_at, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (entry_id, password_encrypted, strength_score, now, reason)
        )
        connection.commit()
        return cursor.lastrowid
    except Exception as error:
        print(f"[PasswordHistory] Failed to add record: {error}")
        return None
    finally:
        connection.close()


def get_history_for_entry(entry_id: int) -> list[PasswordHistoryRecord]:
    """
    Get all history records for an entry, newest first.

    Args:
        entry_id: The password entry ID.

    Returns:
        A list of PasswordHistoryRecord objects.
    """
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT * FROM password_history
            WHERE entry_id = ?
            ORDER BY changed_at DESC
            """,
            (entry_id,)
        )
        return [
            PasswordHistoryRecord(
                id                 = row["id"],
                entry_id           = row["entry_id"],
                password_encrypted = row["password_encrypted"],
                strength_score     = row["strength_score"],
                changed_at         = row["changed_at"],
                reason             = row["reason"]
            )
            for row in cursor.fetchall()
        ]
    except Exception:
        return []
    finally:
        connection.close()


def get_history_record(record_id: int) -> Optional[PasswordHistoryRecord]:
    """Get a specific history record by ID."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM password_history WHERE id = ?",
            (record_id,)
        )
        row = cursor.fetchone()
        if row:
            return PasswordHistoryRecord(
                id                 = row["id"],
                entry_id           = row["entry_id"],
                password_encrypted = row["password_encrypted"],
                strength_score     = row["strength_score"],
                changed_at         = row["changed_at"],
                reason             = row["reason"]
            )
        return None
    finally:
        connection.close()


def delete_history_for_entry(entry_id: int) -> None:
    """Delete all history for an entry (called on entry delete)."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM password_history WHERE entry_id = ?",
            (entry_id,)
        )
        connection.commit()
    finally:
        connection.close()


def count_history_for_entry(entry_id: int) -> int:
    """Return the number of history records for an entry."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM password_history WHERE entry_id = ?",
            (entry_id,)
        )
        return cursor.fetchone()[0]
    except Exception:
        return 0
    finally:
        connection.close()
