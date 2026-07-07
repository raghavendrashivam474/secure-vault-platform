"""
vaultcore/recent_activity.py

Recent Activity Service for the Secure Vault Platform.

Tracks important platform events for display in the
activity feed. Complements the Event Bus by persisting
noteworthy events to the database.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass


DATABASE_PATH: Path = Path("database") / "vault.db"


@dataclass
class ActivityEntry:
    """
    Represents a single activity feed entry.

    Attributes:
        id:          Primary key.
        activity:    Event name (e.g. 'DocumentImported').
        module_id:   Originating module.
        detail:      Optional detail text.
        created_at:  ISO 8601 timestamp.
    """
    id:         Optional[int]
    activity:   str
    module_id:  str
    detail:     str
    created_at: str


class RecentActivityService:
    """
    Tracks and retrieves platform activity events.

    Stores events in SQLite for dashboard display.
    """

    def __init__(self) -> None:
        """Initialize the Recent Activity Service."""
        self._initialize_table()

    def _initialize_table(self) -> None:
        """Create the activity table if it does not exist."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity   TEXT    NOT NULL,
                    module_id  TEXT    NOT NULL DEFAULT 'platform',
                    detail     TEXT,
                    created_at TEXT    NOT NULL
                )
            """)
            connection.commit()
        finally:
            connection.close()

    def record(
        self,
        activity: str,
        module_id: str = "platform",
        detail: str = ""
    ) -> None:
        """
        Record a new activity entry.

        Args:
            activity:  The event name.
            module_id: The originating module.
            detail:    Optional detail text.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            now    = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                INSERT INTO activity (activity, module_id, detail, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (activity, module_id, detail, now)
            )
            connection.commit()
        except Exception:
            pass
        finally:
            connection.close()

    def get_recent(self, limit: int = 50) -> list[ActivityEntry]:
        """
        Return the most recent activity entries.

        Args:
            limit: Maximum entries to return.

        Returns:
            A list of ActivityEntry objects.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM activity ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [
                ActivityEntry(
                    id         = row["id"],
                    activity   = row["activity"],
                    module_id  = row["module_id"],
                    detail     = row["detail"] or "",
                    created_at = row["created_at"]
                )
                for row in cursor.fetchall()
            ]
        finally:
            connection.close()

    def get_count(self) -> int:
        """Return the total activity entry count."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM activity")
            return cursor.fetchone()[0]
        except Exception:
            return 0
        finally:
            connection.close()

    def clear_old(self, keep_last: int = 500) -> None:
        """
        Delete old activity entries keeping only the most recent.

        Args:
            keep_last: Number of recent entries to keep.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("""
                DELETE FROM activity
                WHERE id NOT IN (
                    SELECT id FROM activity
                    ORDER BY created_at DESC
                    LIMIT ?
                )
            """, (keep_last,))
            connection.commit()
        except Exception:
            pass
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        """Open a database connection."""
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        return connection
