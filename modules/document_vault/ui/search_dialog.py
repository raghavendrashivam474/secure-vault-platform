"""
ui/search_dialog.py

Search bar widget for the Personal Document Vault.
Provides a real-time search input that notifies the dashboard.
"""

import tkinter as tk
from typing import Callable


# ── Colours ───────────────────────────────────────────────────────────────────

COLOUR_TOOLBAR  = "#16213e"
COLOUR_ENTRY_BG = "#0d1b2a"
COLOUR_TEXT     = "#eaeaea"
COLOUR_SUBTLE   = "#a0a0b0"
COLOUR_ACCENT   = "#0f3460"


class SearchBar(tk.Frame):
    """
    Inline search bar embedded in the dashboard toolbar.

    Calls on_search with the current query on every keystroke.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_search: Callable[[str], None]
    ) -> None:
        """
        Initialize the search bar.

        Args:
            parent:    The parent widget.
            on_search: Callback invoked with the query string
                       whenever the user types.
        """
        super().__init__(parent, bg=COLOUR_TOOLBAR)
        self._on_search = on_search
        self._var = tk.StringVar()
        self._var.trace_add("write", self._on_change)
        self._build()

    def _build(self) -> None:
        """Construct the search bar widgets."""
        tk.Label(
            self,
            text="🔍",
            font=("Segoe UI", 11),
            bg=COLOUR_TOOLBAR,
            fg=COLOUR_SUBTLE
        ).pack(side="left", padx=(0, 4))

        self._entry = tk.Entry(
            self,
            textvariable=self._var,
            font=("Segoe UI", 10),
            bg=COLOUR_ENTRY_BG,
            fg=COLOUR_TEXT,
            insertbackground=COLOUR_TEXT,
            relief="flat",
            bd=6,
            width=28
        )
        self._entry.pack(side="left", ipady=4)

        self._clear_btn = tk.Button(
            self,
            text="✕",
            font=("Segoe UI", 9),
            bg=COLOUR_TOOLBAR,
            fg=COLOUR_SUBTLE,
            activebackground=COLOUR_TOOLBAR,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            cursor="hand2",
            command=self.clear
        )
        self._clear_btn.pack(side="left", padx=(2, 0))

    def _on_change(self, *args) -> None:
        """Trigger the search callback on every keystroke."""
        self._on_search(self._var.get())

    def clear(self) -> None:
        """Clear the search input."""
        self._var.set("")

    def get_query(self) -> str:
        """
        Return the current search query.

        Returns:
            The current text in the search entry.
        """
        return self._var.get()

