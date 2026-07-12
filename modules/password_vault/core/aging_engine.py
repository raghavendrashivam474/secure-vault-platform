"""
modules/password_vault/core/aging_engine.py

Password aging analyzer for Password Vault.

Calculates password age from the actual password_changed_at timestamp.
Metadata changes (title, username, notes) do not reset age.
Only real password changes reset age.
"""

from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional
from modules.password_vault.models.password_entry import PasswordEntry


# Aging policy thresholds in days
FRESH_DAYS_MAX     = 90       # 0-89 days     = Fresh
AGING_DAYS_MAX     = 180      # 90-179 days   = Aging
OLD_DAYS_MAX       = 365      # 180-364 days  = Old
                              # 365+ days     = Critical


AGE_STATUS_FRESH    = "fresh"
AGE_STATUS_AGING    = "aging"
AGE_STATUS_OLD      = "old"
AGE_STATUS_CRITICAL = "critical"
AGE_STATUS_UNKNOWN  = "unknown"


AGE_LABELS = {
    AGE_STATUS_FRESH:    "Fresh",
    AGE_STATUS_AGING:    "Aging",
    AGE_STATUS_OLD:      "Old",
    AGE_STATUS_CRITICAL: "Critical",
    AGE_STATUS_UNKNOWN:  "Unknown",
}


@dataclass
class AgingResult:
    """
    Password aging analysis result.

    Attributes:
        entry_id:       Password entry ID.
        age_days:       Days since last password change.
        status:         Aging status constant.
        label:          Human readable label.
    """
    entry_id: int
    age_days: int
    status:   str
    label:    str


def get_password_age_days(entry: PasswordEntry) -> Optional[int]:
    """
    Calculate password age in days from actual password change.

    Args:
        entry: The password entry.

    Returns:
        Age in days, or None if unavailable.
    """
    # Use password_changed_at if available, fallback to modified_at
    timestamp = getattr(entry, "password_changed_at", None) or entry.modified_at

    if not timestamp:
        return None

    try:
        changed = datetime.fromisoformat(timestamp)
        if changed.tzinfo is None:
            changed = changed.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - changed
        return delta.days
    except Exception:
        return None


def classify_age(age_days: Optional[int]) -> str:
    """
    Classify password age into a status.

    Args:
        age_days: The password age in days.

    Returns:
        An age status constant.
    """
    if age_days is None:
        return AGE_STATUS_UNKNOWN

    if age_days < FRESH_DAYS_MAX:
        return AGE_STATUS_FRESH
    elif age_days < AGING_DAYS_MAX:
        return AGE_STATUS_AGING
    elif age_days < OLD_DAYS_MAX:
        return AGE_STATUS_OLD
    else:
        return AGE_STATUS_CRITICAL


def analyze_entry(entry: PasswordEntry) -> AgingResult:
    """
    Analyze a single password entry for aging.

    Args:
        entry: The password entry to analyze.

    Returns:
        An AgingResult object.
    """
    age_days = get_password_age_days(entry)
    status   = classify_age(age_days)
    label    = AGE_LABELS[status]

    return AgingResult(
        entry_id = entry.id,
        age_days = age_days if age_days is not None else 0,
        status   = status,
        label    = label
    )


def analyze_all(entries: list[PasswordEntry]) -> dict[int, AgingResult]:
    """
    Analyze all entries and return results keyed by entry ID.

    Args:
        entries: List of password entries.

    Returns:
        Dictionary mapping entry_id to AgingResult.
    """
    return {entry.id: analyze_entry(entry) for entry in entries}


def get_aging_counts(entries: list[PasswordEntry]) -> dict[str, int]:
    """
    Count entries by aging status.

    Args:
        entries: List of password entries.

    Returns:
        Dictionary mapping status to count.
    """
    counts = {
        AGE_STATUS_FRESH:    0,
        AGE_STATUS_AGING:    0,
        AGE_STATUS_OLD:      0,
        AGE_STATUS_CRITICAL: 0,
        AGE_STATUS_UNKNOWN:  0,
    }

    for entry in entries:
        result = analyze_entry(entry)
        counts[result.status] += 1

    return counts


def get_aging_color(status: str) -> str:
    """
    Return a UI color for an aging status.
    Called by dashboard rendering.
    """
    colors = {
        AGE_STATUS_FRESH:    "#51cf66",   # green
        AGE_STATUS_AGING:    "#ffd43b",   # yellow
        AGE_STATUS_OLD:      "#ff8c42",   # orange
        AGE_STATUS_CRITICAL: "#ff6b6b",   # red
        AGE_STATUS_UNKNOWN:  "#a0a0b0",   # grey
    }
    return colors.get(status, "#a0a0b0")
