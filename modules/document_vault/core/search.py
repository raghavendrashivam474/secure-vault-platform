"""
core/search.py

Search, filter, and sort logic for the Personal Document Vault.
Updated in Sprint 6 to support lifecycle filters.
"""

from typing import Optional
from modules.document_vault.models.document import Document
from modules.document_vault.core.lifecycle import (
    filter_expired,
    filter_expiring_soon,
    filter_integrity_issues
)


SORT_FIELDS: list[str] = [
    "name", "date_added", "last_modified",
    "last_opened", "file_size", "file_type", "category"
]


def matches_query(document: Document, query: str) -> bool:
    """
    Check whether a document matches a search query.

    Searches filename, notes, and file type.

    Args:
        document: The Document to check.
        query:    The search string.

    Returns:
        True if the document matches.
    """
    query = query.strip().lower()
    if not query:
        return True
    fields = [
        document.original_name.lower(),
        (document.notes or "").lower(),
        document.file_type.lower(),
    ]
    return any(query in field for field in fields)


def sort_documents(
    documents: list[Document],
    sort_by: str = "date_added",
    ascending: bool = False
) -> list[Document]:
    """
    Sort a list of documents by a given field.

    Args:
        documents:  The list to sort.
        sort_by:    The field to sort by.
        ascending:  True for ascending order.

    Returns:
        A sorted list of Document objects.
    """
    def sort_key(doc: Document):
        if sort_by == "name":
            return doc.original_name.lower()
        elif sort_by == "date_added":
            return doc.date_added or ""
        elif sort_by == "last_modified":
            return doc.last_modified or ""
        elif sort_by == "last_opened":
            return doc.last_opened_at or ""
        elif sort_by == "file_size":
            return doc.file_size
        elif sort_by == "file_type":
            return doc.file_type.lower()
        elif sort_by == "category":
            return doc.category_id or 0
        return doc.date_added or ""

    return sorted(documents, key=sort_key, reverse=not ascending)


def filter_documents(
    documents: list[Document],
    query: str = "",
    category_id: Optional[int] = None,
    file_type: Optional[str] = None,
    uncategorized_only: bool = False,
    favorites_only: bool = False,
    recently_opened: bool = False,
    expired_only: bool = False,
    expiring_soon_only: bool = False,
    integrity_issues_only: bool = False,
    sort_by: str = "date_added",
    ascending: bool = False
) -> list[Document]:
    """
    Filter and sort a list of documents.

    Args:
        documents:             The full document list.
        query:                 Search string.
        category_id:           Filter to this category.
        file_type:             Filter to this file type.
        uncategorized_only:    Show only uncategorized documents.
        favorites_only:        Show only favorites.
        recently_opened:       Show only recently opened.
        expired_only:          Show only expired documents.
        expiring_soon_only:    Show only expiring soon documents.
        integrity_issues_only: Show only documents with integrity failures.
        sort_by:               Field to sort by.
        ascending:             Sort direction.

    Returns:
        A filtered and sorted list.
    """
    results = documents

    if favorites_only:
        results = [d for d in results if d.is_favorite]

    if recently_opened:
        results = [d for d in results if d.last_opened_at]

    if expired_only:
        results = filter_expired(results)

    if expiring_soon_only:
        results = filter_expiring_soon(results)

    if integrity_issues_only:
        results = filter_integrity_issues(results)

    if category_id is not None:
        results = [d for d in results if d.category_id == category_id]

    if uncategorized_only:
        results = [d for d in results if d.category_id is None]

    if file_type == "image":
        results = [
            d for d in results
            if d.file_type.lower() in ("png", "jpg", "jpeg", "webp")
        ]
    elif file_type:
        results = [
            d for d in results
            if d.file_type.lower() == file_type.lower()
        ]

    if query.strip():
        results = [d for d in results if matches_query(d, query)]

    if recently_opened:
        results = sorted(
            results,
            key=lambda d: d.last_opened_at or "",
            reverse=True
        )
    else:
        results = sort_documents(results, sort_by=sort_by, ascending=ascending)

    return results

