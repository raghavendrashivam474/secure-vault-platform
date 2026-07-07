"""
vaultcore/recent_items.py

Recent Items Service for the Secure Vault Platform.

Maintains a shared list of recently accessed resources
across all modules.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass


DATABASE_PATH: Path = Path("database") / "vault.db"


@dataclass
class RecentItem:
    """
    Represents a recently accessed resource.

    Attributes:
        id:         Primary key.
        item_id:    Module-specific item identifier.
        module_id:  Owning module.
        name:       Display name.
        item_type:  Type category (document, password, etc).
        accessed_at: ISO 8601 timestamp.
    """
    id:          Optional[int]
    item_id:     str
    module_id:   str
    name:        str
    item_type:   str
    accessed_at: str


class RecentItemsService:
    """
    Tracks recently accessed items across all modules.

    Modules record item access.
    Dashboard displays combined recent items list.
    """

    def __init__(self) -> None:
        """Initialize the Recent Items Service."""
        self._initialize_table()

    def _initialize_table(self) -> None:
        """Create the recent_items table if it does not exist."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recent_items (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id     TEXT    NOT NULL,
                    module_id   TEXT    NOT NULL,
                    name        TEXT    NOT NULL,
                    item_type   TEXT    NOT NULL,
                    accessed_at TEXT    NOT NULL,
                    UNIQUE(item_id, module_id)
                )
            """)
            connection.commit()
        finally:
            connection.close()

    def record_access(
        self,
        item_id: str,
        module_id: str,
        name: str,
        item_type: str = "item"
    ) -> None:
        """
        Record access to an item.

        Updates timestamp if already exists.

        Args:
            item_id:   Module-specific identifier.
            module_id: Owning module.
            name:      Display name.
            item_type: Type category.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            now    = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                INSERT INTO recent_items
                    (item_id, module_id, name, item_type, accessed_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(item_id, module_id) DO UPDATE SET
                    name        = excluded.name,
                    accessed_at = excluded.accessed_at
                """,
                (item_id, module_id, name, item_type, now)
            )
            connection.commit()
        except Exception:
            pass
        finally:
            connection.close()

    def get_recent(
        self,
        limit: int = 20,
        module_id: Optional[str] = None
    ) -> list[RecentItem]:
        """
        Return recent items ordered by newest access.

        Args:
            limit:     Maximum items to return.
            module_id: Optional module filter.

        Returns:
            A list of RecentItem objects.
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            if module_id:
                cursor.execute(
                    """
                    SELECT * FROM recent_items
                    WHERE module_id = ?
                    ORDER BY accessed_at DESC
                    LIMIT ?
                    """,
                    (module_id, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM recent_items ORDER BY accessed_at DESC LIMIT ?",
                    (limit,)
                )
            return [
                RecentItem(
                    id          = row["id"],
                    item_id     = row["item_id"],
                    module_id   = row["module_id"],
                    name        = row["name"],
                    item_type   = row["item_type"],
                    accessed_at = row["accessed_at"]
                )
                for row in cursor.fetchall()
            ]
        finally:
            connection.close()

    def clear_module(self, module_id: str) -> None:
        """Clear recent items for a module."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM recent_items WHERE module_id = ?",
                (module_id,)
            )
            connection.commit()
        finally:
            connection.close()

    def clear_all(self) -> None:
        """Clear all recent items."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM recent_items")
            connection.commit()
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        """Open a database connection."""
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        return connection
