"""
core/lifecycle.py

Document lifecycle management for the Personal Document Vault.
Handles expiry date tracking and lifecycle queries.
"""

from datetime import datetime, date, timedelta
from typing import Optional

from modules.document_vault.models.document import Document


# Days threshold for expiring soon warning
EXPIRING_SOON_DAYS: int = 30


def is_expired(expiry_date_str: Optional[str]) -> bool:
    """
    Check whether a document has expired.

    Args:
        expiry_date_str: ISO date string (YYYY-MM-DD) or None.

    Returns:
        True if the document is expired.
    """
    if not expiry_date_str:
        return False
    try:
        expiry = date.fromisoformat(expiry_date_str)
        return expiry < date.today()
    except ValueError:
        return False


def is_expiring_soon(expiry_date_str: Optional[str]) -> bool:
    """
    Check whether a document expires within the warning threshold.

    Args:
        expiry_date_str: ISO date string (YYYY-MM-DD) or None.

    Returns:
        True if the document expires within EXPIRING_SOON_DAYS days.
    """
    if not expiry_date_str:
        return False
    try:
        expiry    = date.fromisoformat(expiry_date_str)
        today     = date.today()
        threshold = today + timedelta(days=EXPIRING_SOON_DAYS)
        return today <= expiry <= threshold
    except ValueError:
        return False


def days_until_expiry(expiry_date_str: Optional[str]) -> Optional[int]:
    """
    Calculate the number of days until a document expires.

    Args:
        expiry_date_str: ISO date string (YYYY-MM-DD) or None.

    Returns:
        Number of days until expiry, negative if already expired,
        or None if no expiry date is set.
    """
    if not expiry_date_str:
        return None
    try:
        expiry = date.fromisoformat(expiry_date_str)
        delta  = expiry - date.today()
        return delta.days
    except ValueError:
        return None


def get_expiry_status_label(expiry_date_str: Optional[str]) -> str:
    """
    Return a human-readable expiry status label.

    Args:
        expiry_date_str: ISO date string (YYYY-MM-DD) or None.

    Returns:
        A status string for display in the UI.
    """
    if not expiry_date_str:
        return "No expiry date"

    days = days_until_expiry(expiry_date_str)

    if days is None:
        return "No expiry date"
    elif days < 0:
        return f"Expired {abs(days)} days ago"
    elif days == 0:
        return "Expires today"
    elif days <= EXPIRING_SOON_DAYS:
        return f"Expires in {days} days"
    else:
        return f"Valid until {expiry_date_str}"


def filter_expired(documents: list[Document]) -> list[Document]:
    """
    Return only expired documents.

    Args:
        documents: The full document list.

    Returns:
        Documents whose expiry date is in the past.
    """
    return [d for d in documents if is_expired(d.expiry_date)]


def filter_expiring_soon(documents: list[Document]) -> list[Document]:
    """
    Return only documents expiring within the warning threshold.

    Args:
        documents: The full document list.

    Returns:
        Documents expiring within EXPIRING_SOON_DAYS days.
    """
    return [d for d in documents if is_expiring_soon(d.expiry_date)]


def filter_integrity_issues(documents: list[Document]) -> list[Document]:
    """
    Return documents that have failed integrity verification.

    Args:
        documents: The full document list.

    Returns:
        Documents where integrity_status is False.
    """
    return [
        d for d in documents
        if d.integrity_status is False
    ]

