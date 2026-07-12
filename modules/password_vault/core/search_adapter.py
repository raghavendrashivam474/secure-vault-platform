"""
modules/password_vault/core/search_adapter.py

Password Vault search adapter for VaultCore Search Framework.

Translates VaultCore search requests into Password Vault repository queries.
Searches metadata only — never plaintext passwords.
"""

from vaultcore.search_framework import SearchResult
from modules.password_vault.core.database import load_all_passwords


# Fields safe to search
SEARCHABLE_FIELDS = ["title", "username", "url", "notes"]


def password_search_handler(query: str) -> list[SearchResult]:
    """
    Search Password Vault entries by metadata.

    Args:
        query: The search string from VaultCore Search Framework.

    Returns:
        A list of SearchResult objects.
        Passwords are never included.
    """
    query = query.strip().lower()
    if not query:
        return []

    entries = load_all_passwords()
    results: list[SearchResult] = []

    for entry in entries:
        # Build metadata haystack (never includes password)
        haystack = " ".join([
            entry.title.lower(),
            entry.username.lower(),
            (entry.url or "").lower(),
            (entry.notes or "").lower()
        ])

        if query not in haystack:
            continue

        # Build safe snippet
        snippet_parts = []
        if entry.username:
            snippet_parts.append(f"👤 {entry.username}")
        if entry.url:
            snippet_parts.append(f"🌐 {entry.url}")

        results.append(SearchResult(
            item_id   = str(entry.id),
            module_id = "password_vault",
            title     = entry.title,
            snippet   = "  •  ".join(snippet_parts),
            item_type = "password"
        ))

    return results
