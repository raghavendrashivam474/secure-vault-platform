"""
modules/password_vault/core/filter_engine.py

Credential filter and sort engine for Password Vault.

Applies filter rules and sort orders to password entry collections.
UI never implements filter logic directly.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from modules.password_vault.models.password_entry import PasswordEntry


# Filter constants
FILTER_ALL             = "all"
FILTER_FAVORITES       = "favorites"
FILTER_WEAK            = "weak"
FILTER_AGING           = "aging"
FILTER_OLD             = "old"
FILTER_RECENTLY_USED   = "recent"
FILTER_UNCATEGORIZED   = "uncategorized"

# Sort constants
SORT_TITLE            = "title"
SORT_MODIFIED         = "modified"
SORT_ACCESSED         = "accessed"
SORT_OLDEST_PASSWORD  = "oldest"
SORT_STRENGTH         = "strength"

# Age thresholds in days
AGING_DAYS   = 90
OLD_DAYS     = 180


def filter_entries(
    entries: list[PasswordEntry],
    filter_type: str = FILTER_ALL,
    category_id: Optional[int] = None,
    search_query: str = ""
) -> list[PasswordEntry]:
    """
    Apply filter to a collection of password entries.

    Args:
        entries:      The full entry list.
        filter_type:  Filter constant.
        category_id:  Optional category filter.
        search_query: Optional search text (metadata only).

    Returns:
        Filtered list of password entries.
    """
    results = entries

    # Category filter
    if category_id is not None:
        results = [e for e in results if e.category_id == category_id]

    # Type filter
    if filter_type == FILTER_FAVORITES:
        results = [e for e in results if e.is_favorite]

    elif filter_type == FILTER_WEAK:
        results = [e for e in results if e.strength_score < 60]

    elif filter_type == FILTER_AGING:
        results = [e for e in results if _password_age_days(e) >= AGING_DAYS and _password_age_days(e) < OLD_DAYS]

    elif filter_type == FILTER_OLD:
        results = [e for e in results if _password_age_days(e) >= OLD_DAYS]

    elif filter_type == FILTER_RECENTLY_USED:
        results = [e for e in results if e.last_accessed]

    elif filter_type == FILTER_UNCATEGORIZED:
        results = [e for e in results if e.category_id is None]

    # Search filter (metadata only)
    if search_query.strip():
        q = search_query.strip().lower()
        results = [
            e for e in results
            if q in e.title.lower()
            or q in e.username.lower()
            or q in (e.url or "").lower()
            or q in (e.notes or "").lower()
        ]

    return results


def sort_entries(
    entries: list[PasswordEntry],
    sort_by: str = SORT_TITLE,
    ascending: bool = True
) -> list[PasswordEntry]:
    """
    Sort a collection of password entries.

    Args:
        entries:   The entries to sort.
        sort_by:   Sort constant.
        ascending: True for A-Z, oldest first, etc.

    Returns:
        Sorted list of password entries.
    """
    def sort_key(entry: PasswordEntry):
        if sort_by == SORT_TITLE:
            return entry.title.lower()
        elif sort_by == SORT_MODIFIED:
            return entry.modified_at or ""
        elif sort_by == SORT_ACCESSED:
            return entry.last_accessed or ""
        elif sort_by == SORT_OLDEST_PASSWORD:
            return entry.modified_at or ""
        elif sort_by == SORT_STRENGTH:
            return entry.strength_score
        return entry.title.lower()

    return sorted(entries, key=sort_key, reverse=not ascending)


def _password_age_days(entry: PasswordEntry) -> int:
    """
    Calculate password age in days.

    Uses modified_at as a proxy for last password change.
    Sprint 13.4 will improve this via password history.
    """
    if not entry.modified_at:
        return 0
    try:
        modified = datetime.fromisoformat(entry.modified_at)
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - modified
        return delta.days
    except Exception:
        return 0
