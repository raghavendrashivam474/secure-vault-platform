"""
vaultcore/search_framework.py

Global Search Framework for the Secure Vault Platform.

Modules expose search adapters. VaultCore coordinates
query routing, result aggregation, and history.
"""

from typing import Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SearchResult:
    """
    Represents a single search result.

    Attributes:
        item_id:   Module-specific identifier.
        module_id: Source module.
        title:     Result title.
        snippet:   Preview text.
        item_type: Type category.
    """
    item_id:   str
    module_id: str
    title:     str
    snippet:   str = ""
    item_type: str = "item"


@dataclass
class SearchAdapter:
    """
    Represents a module-provided search adapter.

    Attributes:
        module_id: Owning module.
        handler:   Callable(query) -> list[SearchResult].
    """
    module_id: str
    handler:   Callable


class SearchFramework:
    """
    Coordinates search across all platform modules.

    Modules register adapters.
    Queries are dispatched to all adapters.
    Results are aggregated and returned.
    """

    def __init__(self) -> None:
        """Initialize the search framework."""
        self._adapters: dict[str, SearchAdapter] = {}
        self._history:  list[str] = []

    def register_adapter(self, adapter: SearchAdapter) -> None:
        """
        Register a module search adapter.

        Args:
            adapter: The SearchAdapter to register.
        """
        self._adapters[adapter.module_id] = adapter

    def search(
        self,
        query: str,
        module_id: Optional[str] = None
    ) -> list[SearchResult]:
        """
        Execute a search query.

        Args:
            query:     The search string.
            module_id: Optional module to search within.

        Returns:
            A combined list of SearchResult objects.
        """
        query = query.strip()
        if not query:
            return []

        self._record_history(query)
        results: list[SearchResult] = []

        adapters = (
            [self._adapters[module_id]] if module_id in self._adapters
            else list(self._adapters.values())
        )

        for adapter in adapters:
            try:
                module_results = adapter.handler(query)
                if module_results:
                    results.extend(module_results)
            except Exception:
                pass

        return results

    def get_history(self, limit: int = 20) -> list[str]:
        """
        Return recent search queries.

        Args:
            limit: Maximum entries to return.

        Returns:
            List of recent query strings.
        """
        return self._history[-limit:][::-1]

    def clear_history(self) -> None:
        """Clear the search history."""
        self._history.clear()

    def _record_history(self, query: str) -> None:
        """Add a query to history, removing duplicates."""
        if query in self._history:
            self._history.remove(query)
        self._history.append(query)
        if len(self._history) > 100:
            self._history = self._history[-100:]

    def get_registered_modules(self) -> list[str]:
        """Return module IDs with registered adapters."""
        return list(self._adapters.keys())
