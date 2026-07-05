"""
ui/sidebar.py

Sidebar navigation for the Personal Document Vault.
Updated in Sprint 6 to include Expiring Soon,
Expired, and Integrity Issues filters.
"""

import tkinter as tk
from tkinter import simpledialog, messagebox
from typing import Callable, Optional

from modules.document_vault.models.category import Category
from modules.document_vault.core.categories import validate_category_name
from vaultcore.database import (
    load_all_categories,
    insert_category,
    update_category,
    delete_category,
    get_uncategorized_count,
    load_favorite_documents,
    load_recently_opened_documents
)


COLOUR_SIDEBAR   = "#16213e"
COLOUR_ACCENT    = "#0f3460"
COLOUR_HIGHLIGHT = "#e94560"
COLOUR_TEXT      = "#eaeaea"
COLOUR_SUBTLE    = "#a0a0b0"
COLOUR_HOVER     = "#1a2f5a"
COLOUR_WARNING   = "#ffd43b"
COLOUR_ERROR     = "#ff6b6b"


class Sidebar(tk.Frame):
    """
    Left navigation panel with categories, favorites,
    recently opened, lifecycle filters, and integrity filters.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_select: Callable[[Optional[int], Optional[str]], None],
        on_lock: Callable
    ) -> None:
        """
        Initialize the sidebar.

        Args:
            parent:    The parent widget.
            on_select: Callback with (category_id, filter_type).
            on_lock:   Lock vault callback.
        """
        super().__init__(parent, bg=COLOUR_SIDEBAR, width=230)
        self.pack_propagate(False)
        self._on_select        = on_select
        self._on_lock          = on_lock
        self._categories:      list[Category] = []
        self._selected_button: Optional[tk.Button] = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        """Construct the sidebar layout."""
        tk.Label(
            self,
            text="🔐",
            font=("Segoe UI", 24),
            bg=COLOUR_SIDEBAR,
            fg=COLOUR_HIGHLIGHT
        ).pack(pady=(20, 2))

        tk.Label(
            self,
            text="Document Vault",
            font=("Segoe UI", 11, "bold"),
            bg=COLOUR_SIDEBAR,
            fg=COLOUR_TEXT
        ).pack(pady=(0, 14))

        tk.Frame(self, bg=COLOUR_ACCENT, height=1).pack(fill="x", padx=16)

        # Library section
        self._section_label("LIBRARY")
        self._btn_all = self._nav_btn(
            "📁  All Documents", lambda: self._select(None, "all")
        )
        self._nav_btn("⭐  Favorites",        lambda: self._select(None, "favorites"))
        self._nav_btn("🕒  Recently Opened",  lambda: self._select(None, "recent"))
        self._nav_btn("📂  Uncategorized",    lambda: self._select(None, "uncategorized"))

        tk.Frame(self, bg=COLOUR_ACCENT, height=1).pack(fill="x", padx=16, pady=(8, 0))

        # File type section
        self._section_label("FILE TYPE")
        self._nav_btn("📄  PDFs",   lambda: self._select(None, "pdf"))
        self._nav_btn("🖼  Images", lambda: self._select(None, "image"))

        tk.Frame(self, bg=COLOUR_ACCENT, height=1).pack(fill="x", padx=16, pady=(8, 0))

        # Lifecycle section
        self._section_label("LIFECYCLE")
        self._nav_btn(
            "⏰  Expiring Soon",
            lambda: self._select(None, "expiring_soon"),
            fg=COLOUR_WARNING
        )
        self._nav_btn(
            "❌  Expired",
            lambda: self._select(None, "expired"),
            fg=COLOUR_ERROR
        )
        self._nav_btn(
            "⚠  Integrity Issues",
            lambda: self._select(None, "integrity_issues"),
            fg=COLOUR_ERROR
        )

        tk.Frame(self, bg=COLOUR_ACCENT, height=1).pack(fill="x", padx=16, pady=(8, 0))

        # Categories section
        cat_header = tk.Frame(self, bg=COLOUR_SIDEBAR)
        cat_header.pack(fill="x", padx=16, pady=(10, 4))

        tk.Label(
            cat_header,
            text="CATEGORIES",
            font=("Segoe UI", 8, "bold"),
            bg=COLOUR_SIDEBAR,
            fg=COLOUR_SUBTLE
        ).pack(side="left")

        tk.Button(
            cat_header,
            text="＋",
            font=("Segoe UI", 11, "bold"),
            bg=COLOUR_SIDEBAR,
            fg=COLOUR_HIGHLIGHT,
            activebackground=COLOUR_SIDEBAR,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            cursor="hand2",
            command=self._handle_add_category
        ).pack(side="right")

        # Scrollable category list
        canvas = tk.Canvas(self, bg=COLOUR_SIDEBAR, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="top", fill="both", expand=True)

        self._cat_frame = tk.Frame(canvas, bg=COLOUR_SIDEBAR)
        self._cat_window = canvas.create_window(
            (0, 0), window=self._cat_frame, anchor="nw"
        )
        self._cat_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self._cat_window, width=e.width)
        )

        self._mark_selected(self._btn_all)

    def _section_label(self, text: str) -> None:
        """Render a section header."""
        tk.Label(
            self,
            text=text,
            font=("Segoe UI", 8, "bold"),
            bg=COLOUR_SIDEBAR,
            fg=COLOUR_SUBTLE
        ).pack(anchor="w", padx=18, pady=(12, 4))

    def _nav_btn(
        self,
        label: str,
        command: Callable,
        fg: str = None
    ) -> tk.Button:
        """Create and pack a navigation button."""
        fg_colour = fg or COLOUR_TEXT
        btn = tk.Button(
            self,
            text=label,
            font=("Segoe UI", 10),
            bg=COLOUR_SIDEBAR,
            fg=fg_colour,
            activebackground=COLOUR_HOVER,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            anchor="w",
            padx=18,
            pady=7,
            cursor="hand2",
            command=lambda: [self._mark_selected(btn), command()]
        )
        btn.pack(fill="x")
        return btn

    def refresh(self) -> None:
        """Reload categories from the database and redraw."""
        self._categories = load_all_categories()
        self._render_categories()

    def _render_categories(self) -> None:
        """Render all category buttons."""
        for widget in self._cat_frame.winfo_children():
            widget.destroy()
        for category in self._categories:
            self._render_category_row(category)

    def _render_category_row(self, category: Category) -> None:
        """Render a single category row with context menu."""
        row = tk.Frame(self._cat_frame, bg=COLOUR_SIDEBAR)
        row.pack(fill="x")

        count = f"  ({category.document_count})" if category.document_count > 0 else ""

        btn = tk.Button(
            row,
            text=f"🗂  {category.name}{count}",
            font=("Segoe UI", 10),
            bg=COLOUR_SIDEBAR,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HOVER,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            anchor="w",
            padx=18,
            pady=7,
            cursor="hand2",
            command=lambda c=category: [
                self._mark_selected(btn),
                self._select(c.id, None)
            ]
        )
        btn.pack(side="left", fill="x", expand=True)

        menu = tk.Menu(self, tearoff=0, bg=COLOUR_ACCENT, fg=COLOUR_TEXT)
        menu.add_command(
            label="Rename",
            command=lambda c=category: self._handle_rename_category(c)
        )
        menu.add_command(
            label="Delete",
            command=lambda c=category: self._handle_delete_category(c)
        )
        btn.bind(
            "<Button-3>",
            lambda e, m=menu: m.tk_popup(e.x_root, e.y_root)
        )

    def _select(
        self,
        category_id: Optional[int],
        filter_type: Optional[str]
    ) -> None:
        """Invoke the selection callback."""
        self._on_select(category_id, filter_type)

    def _mark_selected(self, button: tk.Button) -> None:
        """Highlight the active navigation button."""
        if self._selected_button:
            try:
                self._selected_button.config(bg=COLOUR_SIDEBAR)
            except Exception:
                pass
        button.config(bg=COLOUR_ACCENT)
        self._selected_button = button

    def _handle_add_category(self) -> None:
        """Prompt user to create a new category."""
        name = simpledialog.askstring(
            "New Category", "Enter category name:", parent=self
        )
        if not name:
            return
        existing = [c.name for c in self._categories]
        is_valid, error = validate_category_name(name, existing)
        if not is_valid:
            messagebox.showerror("Invalid Name", error, parent=self)
            return
        if insert_category(name) is None:
            messagebox.showerror(
                "Error", "Failed to create category.", parent=self
            )
            return
        self.refresh()

    def _handle_rename_category(self, category: Category) -> None:
        """Prompt user to rename a category."""
        name = simpledialog.askstring(
            "Rename Category",
            f"Rename '{category.name}' to:",
            initialvalue=category.name,
            parent=self
        )
        if not name or name.strip() == category.name:
            return
        existing = [c.name for c in self._categories]
        is_valid, error = validate_category_name(
            name, existing, current_name=category.name
        )
        if not is_valid:
            messagebox.showerror("Invalid Name", error, parent=self)
            return
        if not update_category(category.id, name):
            messagebox.showerror(
                "Error", "Failed to rename category.", parent=self
            )
            return
        self.refresh()

    def _handle_delete_category(self, category: Category) -> None:
        """Confirm and delete a category."""
        confirmed = messagebox.askyesno(
            "Delete Category",
            f"Delete '{category.name}'?\n\nDocuments will become uncategorized.",
            parent=self
        )
        if not confirmed:
            return
        if not delete_category(category.id):
            messagebox.showerror(
                "Error", "Failed to delete category.", parent=self
            )
            return
        self.refresh()
        self._on_select(None, "all")

