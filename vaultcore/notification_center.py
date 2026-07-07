"""
vaultcore/notification_center.py

Persistent Notification Center for the Secure Vault Platform.

Extends the existing toast notification system with
history tracking, categorization, severity, and dismiss support.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

from vaultcore.logger import log_debug


DATABASE_PATH: Path = Path("database") / "vault.db"


@dataclass
class Notification:
    """
    Represents a single platform notification.

    Attributes:
        id:         Primary key.
        title:      Short notification title.
        message:    Full notification text.
        severity:   info, success, warning, error.
        module_id:  Originating module.
        created_at: ISO 8601 timestamp.
        is_read:    True if user has viewed it.
    """
    id:         Optional[int]
    title:      str
    message:    str
    severity:   str
    module_id:  str
    created_at: str
    is_read:    bool


class NotificationCenter:
    """
    Persistent notification history for the Secure Vault Platform.

    Stores all notifications in SQLite for later review.
    Provides read/unread tracking and dismissal.
    """

    def __init__(self) -> None:
        """Initialize the Notification Center."""
        self._initialize_table()

    def _initialize_table(self) -> None:
        """Create the notifications table if it does not exist."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    title      TEXT    NOT NULL,
                    message    TEXT    NOT NULL,
                    severity   TEXT    NOT NULL DEFAULT 'info',
                    module_id  TEXT    NOT NULL DEFAULT 'platform',
                    created_at TEXT    NOT NULL,
                    is_read    INTEGER NOT NULL DEFAULT 0
                )
            """)
            connection.commit()
        finally:
            connection.close()

    def add(
        self,
        title: str,
        message: str,
        severity: str = "info",
        module_id: str = "platform"
    ) -> Optional[int]:
        """
        Add a new notification.

        Args:
            title:     Short title.
            message:   Full text.
            severity:  info, success, warning, or error.
            module_id: The originating module.

        Returns:
            The new notification ID or None on failure.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            now    = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                INSERT INTO notifications
                    (title, message, severity, module_id, created_at, is_read)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (title, message, severity, module_id, now)
            )
            connection.commit()
            log_debug(f"[NotificationCenter] Added: {title}")
            return cursor.lastrowid
        except Exception as error:
            log_debug(f"[NotificationCenter] Add failed: {error}")
            return None
        finally:
            connection.close()

    def get_all(self, limit: int = 100) -> list[Notification]:
        """
        Return all notifications ordered by newest first.

        Args:
            limit: Maximum number to return.

        Returns:
            A list of Notification objects.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [
                Notification(
                    id         = row["id"],
                    title      = row["title"],
                    message    = row["message"],
                    severity   = row["severity"],
                    module_id  = row["module_id"],
                    created_at = row["created_at"],
                    is_read    = bool(row["is_read"])
                )
                for row in cursor.fetchall()
            ]
        finally:
            connection.close()

    def get_unread_count(self) -> int:
        """
        Return the number of unread notifications.

        Returns:
            Unread count as integer.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM notifications WHERE is_read = 0"
            )
            return cursor.fetchone()[0]
        except Exception:
            return 0
        finally:
            connection.close()

    def mark_read(self, notification_id: int) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: The notification to update.

        Returns:
            True if marked successfully.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = ?",
                (notification_id,)
            )
            connection.commit()
            return cursor.rowcount > 0
        except Exception:
            return False
        finally:
            connection.close()

    def mark_all_read(self) -> None:
        """Mark all notifications as read."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE notifications SET is_read = 1")
            connection.commit()
        finally:
            connection.close()

    def dismiss(self, notification_id: int) -> bool:
        """
        Delete a notification.

        Args:
            notification_id: The notification to delete.

        Returns:
            True if deleted successfully.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM notifications WHERE id = ?",
                (notification_id,)
            )
            connection.commit()
            return cursor.rowcount > 0
        except Exception:
            return False
        finally:
            connection.close()

    def clear_all(self) -> None:
        """Delete all notifications."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM notifications")
            connection.commit()
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        """Open a database connection."""
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        return connection
