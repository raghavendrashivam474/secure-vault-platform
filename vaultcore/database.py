"""
core/database.py

Database connection, schema, and all queries
for the Personal Document Vault.
Updated in Sprint 6 to support checksum, expiry,
integrity status, and verification timestamp.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from modules.document_vault.models.document import Document
from modules.document_vault.models.category import Category


DATABASE_PATH: Path = Path("database") / "vault.db"


# ── Connection ────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Open and return a connection to the SQLite database."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# ── Schema and migrations ─────────────────────────────────────────────────────

def initialize_database() -> None:
    """
    Create all required tables and apply pending migrations.
    Safe to call on every application launch.
    """
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id              INTEGER PRIMARY KEY,
                password_hash   TEXT    NOT NULL,
                salt            TEXT    NOT NULL,
                created_at      TEXT    NOT NULL,
                last_opened_at  TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                description TEXT,
                created_at  TEXT    NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid             TEXT    NOT NULL UNIQUE,
                original_name    TEXT    NOT NULL,
                encrypted_name   TEXT    NOT NULL UNIQUE,
                file_type        TEXT    NOT NULL,
                mime_type        TEXT    NOT NULL,
                file_size        INTEGER NOT NULL,
                date_added       TEXT    NOT NULL,
                last_modified    TEXT    NOT NULL,
                notes            TEXT,
                category_id      INTEGER,
                is_favorite      INTEGER NOT NULL DEFAULT 0,
                last_opened_at   TEXT,
                checksum         TEXT,
                expiry_date      TEXT,
                reminder_enabled INTEGER NOT NULL DEFAULT 0,
                integrity_status INTEGER,
                verified_at      TEXT
            )
        """)

        connection.commit()
        _apply_migrations(cursor, connection)
        _seed_default_categories(cursor, connection)

    finally:
        connection.close()


def _apply_migrations(
    cursor: sqlite3.Cursor,
    connection: sqlite3.Connection
) -> None:
    """Apply incremental schema migrations safely."""
    cursor.execute("PRAGMA table_info(documents)")
    existing = {row["name"] for row in cursor.fetchall()}

    migrations = []
    if "uuid" not in existing:
        migrations.append("ALTER TABLE documents ADD COLUMN uuid TEXT")
    if "original_name" not in existing:
        migrations.append("ALTER TABLE documents ADD COLUMN original_name TEXT")
    if "encrypted_name" not in existing:
        migrations.append("ALTER TABLE documents ADD COLUMN encrypted_name TEXT")
    if "mime_type" not in existing:
        migrations.append("ALTER TABLE documents ADD COLUMN mime_type TEXT")
    if "is_favorite" not in existing:
        migrations.append(
            "ALTER TABLE documents ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0"
        )
    if "last_opened_at" not in existing:
        migrations.append("ALTER TABLE documents ADD COLUMN last_opened_at TEXT")
    if "checksum" not in existing:
        migrations.append("ALTER TABLE documents ADD COLUMN checksum TEXT")
    if "expiry_date" not in existing:
        migrations.append("ALTER TABLE documents ADD COLUMN expiry_date TEXT")
    if "reminder_enabled" not in existing:
        migrations.append(
            "ALTER TABLE documents ADD COLUMN reminder_enabled INTEGER NOT NULL DEFAULT 0"
        )
    if "integrity_status" not in existing:
        migrations.append("ALTER TABLE documents ADD COLUMN integrity_status INTEGER")
    if "verified_at" not in existing:
        migrations.append("ALTER TABLE documents ADD COLUMN verified_at TEXT")

    for statement in migrations:
        try:
            cursor.execute(statement)
            print(f"[Database] Migration applied: {statement}")
        except Exception as error:
            print(f"[Database] Migration skipped: {error}")

    if migrations:
        connection.commit()


def _seed_default_categories(
    cursor: sqlite3.Cursor,
    connection: sqlite3.Connection
) -> None:
    """Insert default categories if they do not already exist."""
    from modules.document_vault.core.categories import get_default_categories
    defaults = get_default_categories()
    now = datetime.now(timezone.utc).isoformat()
    for name in defaults:
        cursor.execute(
            "SELECT id FROM categories WHERE LOWER(name) = LOWER(?)", (name,)
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO categories (name, created_at) VALUES (?, ?)",
                (name, now)
            )
    connection.commit()


# ── App settings ──────────────────────────────────────────────────────────────

def save_setting(key: str, value: str) -> None:
    """Save an application setting."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value)
        )
        connection.commit()
    finally:
        connection.close()


def load_setting(key: str, default: str = "") -> str:
    """Load an application setting."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default
    finally:
        connection.close()


def load_all_settings() -> dict[str, str]:
    """Load all application settings."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT key, value FROM app_settings")
        return {row["key"]: row["value"] for row in cursor.fetchall()}
    finally:
        connection.close()


# ── Vault statistics ──────────────────────────────────────────────────────────

def get_vault_statistics() -> dict:
    """Return a dictionary of vault statistics."""
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM categories")
        cat_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM documents WHERE is_favorite = 1")
        fav_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM documents WHERE integrity_status = 0"
        )
        integrity_issues = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM documents "
            "WHERE expiry_date IS NOT NULL AND expiry_date < date('now')"
        )
        expired_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM documents "
            "WHERE expiry_date IS NOT NULL "
            "AND expiry_date >= date('now') "
            "AND expiry_date <= date('now', '+30 days')"
        )
        expiring_count = cursor.fetchone()[0]

        cursor.execute("SELECT created_at FROM settings LIMIT 1")
        row        = cursor.fetchone()
        created_at = row["created_at"][:10] if row else "Unknown"

        cursor.execute("SELECT last_opened_at FROM settings LIMIT 1")
        row         = cursor.fetchone()
        last_opened = (row["last_opened_at"] or "Never")[:10] if row else "Never"

        cursor.execute(
            "SELECT original_name, file_size FROM documents ORDER BY file_size DESC LIMIT 1"
        )
        row          = cursor.fetchone()
        largest_file = f"{row['original_name']} ({row['file_size'] // 1024} KB)" if row else "None"

        return {
            "document_count":    doc_count,
            "category_count":    cat_count,
            "favorite_count":    fav_count,
            "integrity_issues":  integrity_issues,
            "expired_count":     expired_count,
            "expiring_count":    expiring_count,
            "created_at":        created_at,
            "last_opened":       last_opened,
            "largest_file":      largest_file,
        }
    finally:
        connection.close()


# ── Vault settings ────────────────────────────────────────────────────────────

def save_vault_settings(password_hash: str, salt: str) -> None:
    """Save vault master password hash and salt."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM settings")
        cursor.execute(
            "INSERT INTO settings (password_hash, salt, created_at) VALUES (?, ?, ?)",
            (password_hash, salt, datetime.now(timezone.utc).isoformat())
        )
        connection.commit()
    finally:
        connection.close()


def load_vault_settings() -> Optional[sqlite3.Row]:
    """Load vault configuration from the database."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM settings LIMIT 1")
        return cursor.fetchone()
    finally:
        connection.close()


def update_last_opened() -> None:
    """Update the last_opened_at timestamp in vault settings."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE settings SET last_opened_at = ?",
            (datetime.now(timezone.utc).isoformat(),)
        )
        connection.commit()
    finally:
        connection.close()


def vault_exists() -> bool:
    """Check whether a vault has been configured."""
    try:
        return load_vault_settings() is not None
    except Exception:
        return False


# ── Documents ─────────────────────────────────────────────────────────────────

def insert_document(document: Document) -> Optional[int]:
    """Insert a new document record."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO documents (
                uuid, original_name, encrypted_name,
                file_type, mime_type, file_size,
                date_added, last_modified, notes,
                category_id, is_favorite, last_opened_at,
                checksum, expiry_date, reminder_enabled,
                integrity_status, verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.uuid, document.original_name,
                document.encrypted_name, document.file_type,
                document.mime_type, document.file_size,
                document.date_added, document.last_modified,
                document.notes, document.category_id,
                1 if document.is_favorite else 0,
                document.last_opened_at,
                document.checksum,
                document.expiry_date,
                1 if document.reminder_enabled else 0,
                None,
                None,
            )
        )
        connection.commit()
        return cursor.lastrowid
    except Exception as error:
        print(f"[Database] Failed to insert document: {error}")
        return None
    finally:
        connection.close()


def delete_document(document_id: int) -> bool:
    """Delete a document record by ID."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        connection.commit()
        return cursor.rowcount > 0
    except Exception as error:
        print(f"[Database] Failed to delete document: {error}")
        return False
    finally:
        connection.close()


def load_all_documents() -> list[Document]:
    """Load all document records ordered by date added descending."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM documents ORDER BY date_added DESC")
        return [_row_to_document(row) for row in cursor.fetchall()]
    except Exception as error:
        print(f"[Database] Failed to load documents: {error}")
        return []
    finally:
        connection.close()


def get_document_by_checksum(checksum: str) -> Optional[Document]:
    """
    Find an existing document by SHA-256 checksum.

    Used for duplicate detection during import.

    Args:
        checksum: The SHA-256 hex string to search for.

    Returns:
        A Document object if a match is found, or None.
    """
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM documents WHERE checksum = ? LIMIT 1",
            (checksum,)
        )
        row = cursor.fetchone()
        return _row_to_document(row) if row else None
    finally:
        connection.close()


def update_document_metadata(
    document_id: int,
    notes: Optional[str],
    category_id: Optional[int],
    expiry_date: Optional[str] = None,
    reminder_enabled: bool = False
) -> bool:
    """Update notes, category, expiry, and reminder for a document."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE documents
            SET notes = ?, category_id = ?,
                expiry_date = ?, reminder_enabled = ?
            WHERE id = ?
            """,
            (notes, category_id, expiry_date,
             1 if reminder_enabled else 0, document_id)
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception as error:
        print(f"[Database] Failed to update metadata: {error}")
        return False
    finally:
        connection.close()


def update_integrity_status(
    document_id: int,
    status: bool,
    verified_at: str
) -> bool:
    """
    Update the integrity verification result for a document.

    Args:
        document_id: The primary key of the document.
        status:      True if verification passed, False if failed.
        verified_at: ISO 8601 timestamp of verification.

    Returns:
        True if the update succeeded.
    """
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE documents
            SET integrity_status = ?, verified_at = ?
            WHERE id = ?
            """,
            (1 if status else 0, verified_at, document_id)
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception as error:
        print(f"[Database] Failed to update integrity status: {error}")
        return False
    finally:
        connection.close()


def rename_document(document_id: int, new_name: str) -> bool:
    """Update the display name of a document."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE documents SET original_name = ? WHERE id = ?",
            (new_name, document_id)
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception as error:
        print(f"[Database] Failed to rename document: {error}")
        return False
    finally:
        connection.close()


def toggle_favorite(document_id: int, is_favorite: bool) -> bool:
    """Set the favorite status of a document."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE documents SET is_favorite = ? WHERE id = ?",
            (1 if is_favorite else 0, document_id)
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception as error:
        print(f"[Database] Failed to toggle favorite: {error}")
        return False
    finally:
        connection.close()


def update_document_last_opened(document_id: int) -> bool:
    """Update the last_opened_at timestamp for a document."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE documents SET last_opened_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), document_id)
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception as error:
        print(f"[Database] Failed to update last_opened_at: {error}")
        return False
    finally:
        connection.close()


def load_favorite_documents() -> list[Document]:
    """Load all documents marked as favorites."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM documents WHERE is_favorite = 1 ORDER BY original_name ASC"
        )
        return [_row_to_document(row) for row in cursor.fetchall()]
    except Exception as error:
        print(f"[Database] Failed to load favorites: {error}")
        return []
    finally:
        connection.close()


def load_recently_opened_documents(limit: int = 10) -> list[Document]:
    """Load the most recently opened documents."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT * FROM documents
            WHERE last_opened_at IS NOT NULL
            ORDER BY last_opened_at DESC LIMIT ?
            """,
            (limit,)
        )
        return [_row_to_document(row) for row in cursor.fetchall()]
    except Exception as error:
        print(f"[Database] Failed to load recent: {error}")
        return []
    finally:
        connection.close()


def bulk_delete_documents(document_ids: list[int]) -> int:
    """Delete multiple document records."""
    connection = get_connection()
    deleted = 0
    try:
        cursor = connection.cursor()
        for doc_id in document_ids:
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            deleted += cursor.rowcount
        connection.commit()
        return deleted
    except Exception as error:
        print(f"[Database] Bulk delete error: {error}")
        return deleted
    finally:
        connection.close()


def bulk_set_category(
    document_ids: list[int],
    category_id: Optional[int]
) -> int:
    """Assign or remove a category from multiple documents."""
    connection = get_connection()
    updated = 0
    try:
        cursor = connection.cursor()
        for doc_id in document_ids:
            cursor.execute(
                "UPDATE documents SET category_id = ? WHERE id = ?",
                (category_id, doc_id)
            )
            updated += cursor.rowcount
        connection.commit()
        return updated
    except Exception as error:
        print(f"[Database] Bulk category error: {error}")
        return updated
    finally:
        connection.close()


def bulk_set_favorite(
    document_ids: list[int],
    is_favorite: bool
) -> int:
    """Set favorite status on multiple documents."""
    connection = get_connection()
    updated = 0
    try:
        cursor = connection.cursor()
        value = 1 if is_favorite else 0
        for doc_id in document_ids:
            cursor.execute(
                "UPDATE documents SET is_favorite = ? WHERE id = ?",
                (value, doc_id)
            )
            updated += cursor.rowcount
        connection.commit()
        return updated
    except Exception as error:
        print(f"[Database] Bulk favorite error: {error}")
        return updated
    finally:
        connection.close()


def _row_to_document(row: sqlite3.Row) -> Document:
    """Convert a database row to a Document object."""
    integrity_raw = row["integrity_status"]
    integrity = None
    if integrity_raw == 1:
        integrity = True
    elif integrity_raw == 0:
        integrity = False

    return Document(
        id               = row["id"],
        uuid             = row["uuid"],
        original_name    = row["original_name"],
        encrypted_name   = row["encrypted_name"],
        file_type        = row["file_type"],
        mime_type        = row["mime_type"],
        file_size        = row["file_size"],
        date_added       = row["date_added"],
        last_modified    = row["last_modified"],
        notes            = row["notes"],
        category_id      = row["category_id"],
        is_favorite      = bool(row["is_favorite"]),
        last_opened_at   = row["last_opened_at"],
        checksum         = row["checksum"],
        expiry_date      = row["expiry_date"],
        reminder_enabled = bool(row["reminder_enabled"]),
        integrity_status = integrity,
        verified_at      = row["verified_at"]
    )


# ── Categories ────────────────────────────────────────────────────────────────

def insert_category(name: str, description: Optional[str] = None) -> Optional[int]:
    """Insert a new category."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO categories (name, description, created_at) VALUES (?, ?, ?)",
            (name.strip(), description, datetime.now(timezone.utc).isoformat())
        )
        connection.commit()
        return cursor.lastrowid
    except Exception as error:
        print(f"[Database] Failed to insert category: {error}")
        return None
    finally:
        connection.close()


def update_category(category_id: int, name: str) -> bool:
    """Rename an existing category."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE categories SET name = ? WHERE id = ?",
            (name.strip(), category_id)
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception as error:
        print(f"[Database] Failed to update category: {error}")
        return False
    finally:
        connection.close()


def delete_category(category_id: int) -> bool:
    """Delete a category and unassign all its documents."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE documents SET category_id = NULL WHERE category_id = ?",
            (category_id,)
        )
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        connection.commit()
        return True
    except Exception as error:
        print(f"[Database] Failed to delete category: {error}")
        return False
    finally:
        connection.close()


def load_all_categories() -> list[Category]:
    """Load all categories with document counts."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                c.id, c.name, c.description, c.created_at,
                COUNT(d.id) AS document_count
            FROM categories c
            LEFT JOIN documents d ON d.category_id = c.id
            GROUP BY c.id
            ORDER BY c.name ASC
        """)
        return [
            Category(
                id             = row["id"],
                name           = row["name"],
                description    = row["description"],
                created_at     = row["created_at"],
                document_count = row["document_count"]
            )
            for row in cursor.fetchall()
        ]
    except Exception as error:
        print(f"[Database] Failed to load categories: {error}")
        return []
    finally:
        connection.close()


def get_uncategorized_count() -> int:
    """Return the number of documents with no category."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM documents WHERE category_id IS NULL"
        )
        return cursor.fetchone()[0]
    except Exception:
        return 0
    finally:
        connection.close()




