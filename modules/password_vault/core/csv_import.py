"""
modules/password_vault/core/csv_import.py

Browser CSV import handler for Password Vault.

Recognizes common browser export formats:
Chrome, Firefox, Edge, Safari, Bitwarden, LastPass, etc.
"""

import csv
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# Field aliases for header recognition
FIELD_ALIASES = {
    "title": ["name", "title", "site", "site_name"],
    "url":   ["url", "website", "origin", "web_site", "login_uri"],
    "username": ["username", "user", "login", "email", "user_name"],
    "password": ["password", "pass", "login_password"],
    "notes":  ["notes", "note", "comment", "extra"],
}


@dataclass
class ImportRow:
    """
    Represents a single row parsed from CSV.

    Attributes:
        title:    Entry title (required).
        username: Username (required).
        password: Password (required).
        url:      Optional website.
        notes:    Optional notes.
        row_num:  Original CSV row number.
        is_valid: True if row has required fields.
        error:    Validation error if invalid.
        is_duplicate: True if likely duplicate of existing entry.
    """
    title:        str
    username:     str
    password:     str
    url:          Optional[str] = None
    notes:        Optional[str] = None
    row_num:      int  = 0
    is_valid:     bool = True
    error:        Optional[str] = None
    is_duplicate: bool = False


@dataclass
class ImportReport:
    """
    Import operation summary.

    Attributes:
        rows_found:  Total rows parsed from CSV.
        imported:    Successfully imported.
        skipped:     Skipped by user.
        duplicates:  Skipped as duplicates.
        invalid:     Rejected as invalid.
        failed:      Failed during encryption/storage.
    """
    rows_found:  int  = 0
    imported:    int  = 0
    skipped:     int  = 0
    duplicates:  int  = 0
    invalid:     int  = 0
    failed:      int  = 0


def _normalize_header(header: str) -> str:
    """Normalize a CSV header for matching."""
    return header.strip().lower().replace(" ", "_").replace("-", "_")


def _detect_field(headers: list[str], aliases: list[str]) -> Optional[str]:
    """
    Find the actual header name matching one of the aliases.

    Args:
        headers: All CSV headers (normalized).
        aliases: Aliases to search for.

    Returns:
        The matching header, or None.
    """
    for alias in aliases:
        alias_norm = _normalize_header(alias)
        for header in headers:
            if _normalize_header(header) == alias_norm:
                return header
    return None


def parse_csv(file_path: Path) -> tuple[list[ImportRow], Optional[str]]:
    """
    Parse a browser CSV export.

    Args:
        file_path: Path to CSV file.

    Returns:
        Tuple of (rows, error_message).
        error_message is None on success.
    """
    rows: list[ImportRow] = []

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames:
                return [], "CSV file has no headers."

            # Detect field mappings
            title_field    = _detect_field(reader.fieldnames, FIELD_ALIASES["title"])
            url_field      = _detect_field(reader.fieldnames, FIELD_ALIASES["url"])
            username_field = _detect_field(reader.fieldnames, FIELD_ALIASES["username"])
            password_field = _detect_field(reader.fieldnames, FIELD_ALIASES["password"])
            notes_field    = _detect_field(reader.fieldnames, FIELD_ALIASES["notes"])

            if not username_field or not password_field:
                return [], "CSV must contain username and password columns."

            for row_num, row in enumerate(reader, start=2):
                title    = (row.get(title_field, "") if title_field else "").strip()
                url      = (row.get(url_field, "") if url_field else "").strip()
                username = (row.get(username_field, "") if username_field else "").strip()
                password = (row.get(password_field, "") if password_field else "").strip()
                notes    = (row.get(notes_field, "") if notes_field else "").strip()

                # Use URL as fallback title
                if not title and url:
                    title = _extract_title_from_url(url)

                # Validate
                is_valid = True
                error    = None

                if not title:
                    is_valid = False
                    error = "Missing title"
                elif not username:
                    is_valid = False
                    error = "Missing username"
                elif not password:
                    is_valid = False
                    error = "Missing password"

                rows.append(ImportRow(
                    title    = title,
                    username = username,
                    password = password,
                    url      = url or None,
                    notes    = notes or None,
                    row_num  = row_num,
                    is_valid = is_valid,
                    error    = error
                ))

        return rows, None

    except UnicodeDecodeError:
        return [], "CSV file encoding not supported. Use UTF-8."
    except Exception as error:
        return [], f"Failed to parse CSV: {error}"


def _extract_title_from_url(url: str) -> str:
    """Extract a display title from a URL."""
    if not url:
        return ""
    clean = url.replace("https://", "").replace("http://", "")
    clean = clean.split("/")[0]
    clean = clean.replace("www.", "")
    return clean.split(".")[0].capitalize() if clean else "Untitled"


def _normalize_website(url: Optional[str]) -> str:
    """Normalize a URL for duplicate comparison."""
    if not url:
        return ""
    clean = url.lower().strip()
    clean = clean.replace("https://", "").replace("http://", "")
    clean = clean.split("/")[0].replace("www.", "")
    return clean


def detect_duplicates(rows: list[ImportRow], existing_entries: list) -> None:
    """
    Mark rows that are likely duplicates of existing entries.

    Duplicate criteria: same normalized website AND same username.

    Args:
        rows:             Parsed CSV rows.
        existing_entries: Current password entries.
    """
    existing_keys = set()
    for entry in existing_entries:
        key = (_normalize_website(entry.url), entry.username.lower().strip())
        existing_keys.add(key)

    for row in rows:
        if not row.is_valid:
            continue
        key = (_normalize_website(row.url), row.username.lower().strip())
        if key in existing_keys:
            row.is_duplicate = True
