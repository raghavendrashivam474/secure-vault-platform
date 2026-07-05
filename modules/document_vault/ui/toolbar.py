"""
ui/toolbar.py

Dynamic toolbar for the Personal Document Vault.
Updated to include Lock Vault button always visible.
"""

import tkinter as tk
from typing import Callable, Optional


COLOUR_TOOLBAR   = "#16213e"
COLOUR_ACCENT    = "#0f3460"
COLOUR_HIGHLIGHT = "#e94560"
COLOUR_TEXT      = "#eaeaea"
COLOUR_SUBTLE    = "#a0a0b0"


SORT_OPTIONS: list[tuple[str, str]] = [
    ("date_added",    "Date Added"),
    ("name",          "Name"),
    ("file_size",     "Size"),
    ("file_type",     "Type"),
    ("last_modified", "Last Modified"),
    ("last_opened",   "Last Opened"),
]


class Toolbar(tk.Frame):
    """
    Dynamic toolbar that adapts to the current selection state.
    Lock Vault button is always visible on the right side.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_import:          Callable,
        on_delete:          Callable,
        on_rename:          Callable,
        on_favorite:        Callable,
        on_bulk_delete:     Callable,
        on_bulk_category:   Callable,
        on_bulk_favorite:   Callable,
        on_sort_change:     Callable[[str, bool], None],
        on_select_all:      Callable,
        on_lock:            Callable,
        on_export:          Callable,
    ) -> None:
        """
        Initialize the toolbar.

        Args:
            parent:           Parent widget.
            on_import:        Import button callback.
            on_delete:        Single delete callback.
            on_rename:        Rename callback.
            on_favorite:      Favorite toggle callback.
            on_bulk_delete:   Bulk delete callback.
            on_bulk_category: Bulk category assign callback.
            on_bulk_favorite: Bulk favorite callback.
            on_sort_change:   Sort change callback (field, ascending).
            on_select_all:    Select all callback.
            on_lock:          Lock vault callback.
        """
        super().__init__(parent, bg=COLOUR_TOOLBAR, height=56)
        self.pack_propagate(False)

        self._on_import        = on_import
        self._on_delete        = on_delete
        self._on_rename        = on_rename
        self._on_favorite      = on_favorite
        self._on_bulk_delete   = on_bulk_delete
        self._on_bulk_category = on_bulk_category
        self._on_bulk_favorite = on_bulk_favorite
        self._on_sort_change   = on_sort_change
        self._on_select_all    = on_select_all
        self._on_lock          = on_lock
        self._on_export        = on_export

        self._sort_by:   str  = "date_added"
        self._ascending: bool = False

        self._build()

    def _build(self) -> None:
        """Construct toolbar layout."""

        # ── Left side — title ─────────────────────────────────────────────────
        self._title_label = tk.Label(
            self,
            text="All Documents",
            font=("Segoe UI", 13, "bold"),
            bg=COLOUR_TOOLBAR,
            fg=COLOUR_TEXT
        )
        self._title_label.pack(side="left", padx=20)

        # Sort dropdown
        self._sort_var = tk.StringVar(value="Date Added")
        sort_menu = tk.OptionMenu(
            self,
            self._sort_var,
            *[label for _, label in SORT_OPTIONS],
            command=self._handle_sort_change
        )
        sort_menu.config(
            font=("Segoe UI", 9),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            highlightthickness=0,
            relief="flat"
        )
        sort_menu["menu"].config(
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            font=("Segoe UI", 9)
        )
        sort_menu.pack(side="left", padx=(8, 0), pady=10)

        # Ascending / Descending toggle
        self._asc_btn = tk.Button(
            self,
            text="↓",
            font=("Segoe UI", 12),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            width=2,
            command=self._toggle_direction
        )
        self._asc_btn.pack(side="left", padx=(2, 0), pady=10)

        # ── Right side — always visible buttons ───────────────────────────────

        # Lock Vault — always visible
        tk.Button(
            self,
            text="🔒  Lock",
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_HIGHLIGHT,
            fg="#ffffff",
            activebackground="#c73652",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._on_lock
        ).pack(side="right", padx=(0, 12), pady=10)

        # Import — always visible
        self._btn_import = tk.Button(
            self,
            text="＋  Import",
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_ACCENT,
            fg="#ffffff",
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._on_import
        )
        self._btn_import.pack(side="right", padx=(0, 6), pady=10)

        # Select All
        self._btn_select_all = tk.Button(
            self,
            text="Select All",
            font=("Segoe UI", 10),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._on_select_all
        )
        self._btn_select_all.pack(side="right", padx=(0, 6), pady=10)

        # ── Context buttons (shown/hidden based on selection) ─────────────────

        self._btn_delete = self._context_button(
            "🗑  Delete", self._on_delete
        )
        self._btn_rename = self._context_button(
            "✏  Rename", self._on_rename
        )
        self._btn_favorite = self._context_button(
            "⭐  Favorite", self._on_favorite
        )
        self._btn_bulk_delete = self._context_button(
            "🗑  Delete All", self._on_bulk_delete, danger=True
        )
        self._btn_bulk_category = self._context_button(
            "🗂  Category", self._on_bulk_category
        )
        self._btn_bulk_favorite = self._context_button(
            "⭐  Favorite All", self._on_bulk_favorite
        )

        self._btn_export = self._context_button(
            "📤  Export", self._on_export
        )

        self.update_state("none")

    def _context_button(
        self,
        text: str,
        command: Callable,
        danger: bool = False
    ) -> tk.Button:
        """Create a context-sensitive button without packing it."""
        bg = "#8b0000" if danger else COLOUR_ACCENT
        return tk.Button(
            self,
            text=text,
            font=("Segoe UI", 10),
            bg=bg,
            fg="#ffffff",
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=command
        )

    def update_state(self, state: str, label: str = "All Documents") -> None:
        """
        Update toolbar buttons based on selection state.

        Args:
            state: One of 'none', 'single', 'multi'.
            label: Title label text.
        """
        self._title_label.config(text=label)

        for btn in [
            self._btn_delete,
            self._btn_rename,
            self._btn_favorite,
            self._btn_bulk_delete,
            self._btn_bulk_category,
            self._btn_bulk_favorite,
            self._btn_export,
        ]:
            btn.pack_forget()

        if state == "single":
            self._btn_export.pack(side="right", padx=(0, 4), pady=10)
            self._btn_delete.pack(side="right", padx=(0, 4), pady=10)
            self._btn_rename.pack(side="right", padx=(0, 4), pady=10)
            self._btn_favorite.pack(side="right", padx=(0, 4), pady=10)

        elif state == "multi":
            self._btn_export.pack(side="right", padx=(0, 4), pady=10)
            self._btn_bulk_delete.pack(side="right", padx=(0, 4), pady=10)
            self._btn_bulk_category.pack(side="right", padx=(0, 4), pady=10)
            self._btn_bulk_favorite.pack(side="right", padx=(0, 4), pady=10)

    def set_title(self, title: str) -> None:
        """Update the toolbar title."""
        self._title_label.config(text=title)

    def _handle_sort_change(self, selected_label: str) -> None:
        """Handle sort dropdown change."""
        for field, label in SORT_OPTIONS:
            if label == selected_label:
                self._sort_by = field
                break
        self._on_sort_change(self._sort_by, self._ascending)

    def _toggle_direction(self) -> None:
        """Toggle sort direction."""
        self._ascending = not self._ascending
        self._asc_btn.config(text="↑" if self._ascending else "↓")
        self._on_sort_change(self._sort_by, self._ascending)


