"""
modules/password_vault/core/database.py

Password Vault database operations.
Uses shared VaultCore database connection.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from modules.password_vault.models.password_entry import PasswordEntry
from modules.password_vault.models.password_category import PasswordCategory


DATABASE_PATH: Path = Path("database") / "vault.db"


DEFAULT_CATEGORIES = [
    ("Personal",     "👤"),
    ("Work",         "💼"),
    ("Finance",      "💳"),
    ("Shopping",     "🛒"),
    ("Development",  "💻"),
    ("Social Media", "🌐"),
]


def _connect() -> sqlite3.Connection:
    """Open a database connection."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_password_database() -> None:
    """Create Password Vault tables and seed defaults."""
    connection = _connect()
    try:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_entries (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                title              TEXT    NOT NULL,
                username           TEXT    NOT NULL,
                password_encrypted TEXT    NOT NULL,
                url                TEXT,
                category_id        INTEGER,
                notes              TEXT,
                is_favorite        INTEGER NOT NULL DEFAULT 0,
                strength_score     INTEGER NOT NULL DEFAULT 0,
                created_at         TEXT    NOT NULL,
                modified_at        TEXT    NOT NULL,
                last_accessed      TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL UNIQUE,
                icon       TEXT    DEFAULT '🔑',
                created_at TEXT    NOT NULL
            )
        """)

        connection.commit()
        _seed_default_categories(cursor, connection)

    finally:
        connection.close()


def _seed_default_categories(cursor, connection) -> None:
    """Insert default categories if missing."""
    now = datetime.now(timezone.utc).isoformat()
    for name, icon in DEFAULT_CATEGORIES:
        cursor.execute(
            "SELECT id FROM password_categories WHERE LOWER(name) = LOWER(?)",
            (name,)
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO password_categories (name, icon, created_at) VALUES (?, ?, ?)",
                (name, icon, now)
            )
    connection.commit()


# ── Password entry operations ─────────────────────────────────────────────────

def insert_password(entry: PasswordEntry) -> Optional[int]:
    """Insert a new password entry."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO password_entries (
                title, username, password_encrypted, url,
                category_id, notes, is_favorite, strength_score,
                created_at, modified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.title, entry.username, entry.password_encrypted,
                entry.url, entry.category_id, entry.notes,
                1 if entry.is_favorite else 0, entry.strength_score,
                now, now
            )
        )
        connection.commit()
        return cursor.lastrowid
    except Exception as error:
        print(f"[PasswordVault] Insert failed: {error}")
        return None
    finally:
        connection.close()


def update_password(entry: PasswordEntry) -> bool:
    """Update an existing password entry."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            UPDATE password_entries
            SET title = ?, username = ?, password_encrypted = ?,
                url = ?, category_id = ?, notes = ?,
                is_favorite = ?, strength_score = ?, modified_at = ?
            WHERE id = ?
            """,
            (
                entry.title, entry.username, entry.password_encrypted,
                entry.url, entry.category_id, entry.notes,
                1 if entry.is_favorite else 0, entry.strength_score,
                now, entry.id
            )
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception as error:
        print(f"[PasswordVault] Update failed: {error}")
        return False
    finally:
        connection.close()


def delete_password(entry_id: int) -> bool:
    """Delete a password entry."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM password_entries WHERE id = ?", (entry_id,))
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        connection.close()


def load_all_passwords() -> list[PasswordEntry]:
    """Load all password entries."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM password_entries ORDER BY title ASC"
        )
        return [_row_to_entry(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        connection.close()


def get_password_by_id(entry_id: int) -> Optional[PasswordEntry]:
    """Get a specific password entry by ID."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM password_entries WHERE id = ?", (entry_id,)
        )
        row = cursor.fetchone()
        return _row_to_entry(row) if row else None
    finally:
        connection.close()


def update_last_accessed(entry_id: int) -> None:
    """Update the last accessed timestamp."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE password_entries SET last_accessed = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), entry_id)
        )
        connection.commit()
    finally:
        connection.close()


def toggle_favorite(entry_id: int, is_favorite: bool) -> bool:
    """Toggle favorite status."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE password_entries SET is_favorite = ? WHERE id = ?",
            (1 if is_favorite else 0, entry_id)
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        connection.close()


# ── Category operations ───────────────────────────────────────────────────────

def load_all_categories() -> list[PasswordCategory]:
    """Load all password categories with entry counts."""
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                c.id, c.name, c.icon, c.created_at,
                COUNT(p.id) AS entry_count
            FROM password_categories c
            LEFT JOIN password_entries p ON p.category_id = c.id
            GROUP BY c.id
            ORDER BY c.name ASC
        """)
        return [
            PasswordCategory(
                id          = row["id"],
                name        = row["name"],
                icon        = row["icon"] or "🔑",
                created_at  = row["created_at"],
                entry_count = row["entry_count"]
            )
            for row in cursor.fetchall()
        ]
    except Exception:
        return []
    finally:
        connection.close()


# ── Statistics ────────────────────────────────────────────────────────────────

def get_password_statistics() -> dict:
    """Return password vault statistics."""
    connection = _connect()
    try:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM password_entries")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM password_entries WHERE is_favorite = 1")
        favorites = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM password_categories")
        categories = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM password_entries WHERE strength_score < 60")
        weak = cursor.fetchone()[0]

        return {
            "total_passwords":    total,
            "favorite_passwords": favorites,
            "categories":         categories,
            "weak_passwords":     weak
        }
    except Exception:
        return {
            "total_passwords":    0,
            "favorite_passwords": 0,
            "categories":         0,
            "weak_passwords":     0
        }
    finally:
        connection.close()


def _row_to_entry(row) -> PasswordEntry:
    """Convert a database row to a PasswordEntry object."""
    return PasswordEntry(
        id                 = row["id"],
        title              = row["title"],
        username           = row["username"],
        password_encrypted = row["password_encrypted"],
        url                = row["url"],
        category_id        = row["category_id"],
        notes              = row["notes"],
        is_favorite        = bool(row["is_favorite"]),
        strength_score     = row["strength_score"],
        created_at         = row["created_at"],
        modified_at        = row["modified_at"],
        last_accessed      = row["last_accessed"]
    )
