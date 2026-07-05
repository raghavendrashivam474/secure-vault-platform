"""
ui/dashboard.py

Main dashboard for the Personal Document Vault.
Updated in Sprint 6 to support lifecycle filters,
duplicate detection, and health panel navigation.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
from pathlib import Path
from typing import Optional, Callable

from modules.document_vault.core.vault import VaultState
from modules.document_vault.core.metadata import extract_metadata
from vaultcore.encryption import encrypt_file, decrypt_file_to_memory
from modules.document_vault.core.search import filter_documents
from modules.document_vault.core.integrity import generate_checksum
from vaultcore.database import (
    insert_document,
    delete_document,
    load_all_documents,
    bulk_delete_documents,
    bulk_set_category,
    bulk_set_favorite,
    load_all_categories,
    get_document_by_checksum
)
from modules.document_vault.models.document import Document
from vaultcore.file_utils import (
    validate_file,
    ensure_vault_directories,
    safe_delete_file,
    VAULT_ENCRYPTED_PATH
)
from modules.document_vault.ui.import_dialog import open_file_dialog
from modules.document_vault.ui.preview_panel import PreviewPanel
from modules.document_vault.ui.sidebar import Sidebar
from modules.document_vault.ui.search_dialog import SearchBar
from modules.document_vault.ui.toolbar import Toolbar


COLOUR_BACKGROUND = "#1a1a2e"
COLOUR_TOOLBAR    = "#16213e"
COLOUR_ACCENT     = "#0f3460"
COLOUR_HIGHLIGHT  = "#e94560"
COLOUR_TEXT       = "#eaeaea"
COLOUR_SUBTLE     = "#a0a0b0"
COLOUR_ITEM_BG    = "#0d1b2a"
COLOUR_SELECTED   = "#0f3460"
COLOUR_WARNING    = "#ffd43b"
COLOUR_ERROR      = "#ff6b6b"

FILE_ICONS: dict[str, str] = {
    "pdf":  "📄",
    "png":  "🖼",
    "jpg":  "🖼",
    "jpeg": "🖼",
    "webp": "🖼",
}


class Dashboard(tk.Frame):
    """
    Main dashboard with lifecycle filters, duplicate detection,
    and health panel navigation.
    """

    def __init__(
        self,
        parent: tk.Widget,
        vault_state: VaultState,
        on_lock: Callable,
        master_password: str,
        on_settings: Callable,
        on_health: Callable
    ) -> None:
        """
        Initialize the dashboard.

        Args:
            parent:          The parent widget.
            vault_state:     Shared vault state.
            on_lock:         Lock vault callback.
            master_password: Session master password.
            on_settings:     Open settings screen callback.
            on_health:       Open health check panel callback.
        """
        super().__init__(parent, bg=COLOUR_BACKGROUND)
        self._vault_state     = vault_state
        self._on_lock         = on_lock
        self._master_password = master_password
        self._on_settings     = on_settings
        self._on_health       = on_health

        self._all_documents:  list[Document] = []
        self._filtered_docs:  list[Document] = []
        self._selected_ids:   set[int]       = set()
        self._item_frames:    dict[int, tk.Frame] = {}

        self._active_category: Optional[int] = None
        self._active_filter:   Optional[str] = "all"
        self._search_query:    str  = ""
        self._sort_by:         str  = "date_added"
        self._ascending:       bool = False

        ensure_vault_directories()
        self._build()
        self._load_documents()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        """Construct the full dashboard layout."""
        self.pack(fill="both", expand=True)

        self._sidebar = Sidebar(
            parent    = self,
            on_select = self._handle_filter_change,
            on_lock   = self._handle_lock
        )
        self._sidebar.pack(side="left", fill="y")

        main = tk.Frame(self, bg=COLOUR_BACKGROUND)
        main.pack(side="left", fill="both", expand=True)

        # Top button row
        btn_row = tk.Frame(main, bg=COLOUR_BACKGROUND)
        btn_row.pack(fill="x", padx=12, pady=(6, 0))

        tk.Button(
            btn_row,
            text="⚙  Settings",
            font=("Segoe UI", 10),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._on_settings
        ).pack(side="right", padx=(4, 0))

        tk.Button(
            btn_row,
            text="📤  Export Vault",
            font=("Segoe UI", 10),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._handle_export_vault
        ).pack(side="right", padx=(4, 0))

        tk.Button(
            btn_row,
            text="🏥  Health Check",
            font=("Segoe UI", 10),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._on_health
        ).pack(side="right", padx=(4, 0))

        self._toolbar = Toolbar(
            parent           = main,
            on_import        = self._handle_import,
            on_delete        = self._handle_single_delete,
            on_rename        = self._handle_rename_selected,
            on_favorite      = self._handle_toggle_favorite_selected,
            on_bulk_delete   = self._handle_bulk_delete,
            on_bulk_category = self._handle_bulk_category,
            on_bulk_favorite = self._handle_bulk_favorite,
            on_sort_change   = self._handle_sort_change,
            on_select_all    = self._handle_select_all,
            on_lock          = self._handle_lock,
            on_export        = self._handle_export_selected,
        )
        self._toolbar.pack(fill="x")

        body = tk.Frame(main, bg=COLOUR_BACKGROUND)
        body.pack(fill="both", expand=True)

        self._build_document_list(body)

        self._preview_panel = PreviewPanel(
            parent            = body,
            on_metadata_saved = self._on_metadata_saved
        )
        self._preview_panel.set_master_password(self._master_password)
        self._preview_panel.pack(side="right", fill="y")

    def _build_document_list(self, parent: tk.Widget) -> None:
        """Build the scrollable document list."""
        self._list_frame = tk.Frame(parent, bg=COLOUR_BACKGROUND)
        self._list_frame.pack(side="left", fill="both", expand=True)

        search_frame = tk.Frame(self._list_frame, bg=COLOUR_TOOLBAR)
        search_frame.pack(fill="x")

        self._search_bar = SearchBar(
            parent    = search_frame,
            on_search = self._handle_search
        )
        self._search_bar.pack(side="left", padx=12, pady=8)

        header = tk.Frame(self._list_frame, bg=COLOUR_ACCENT, height=30)
        header.pack(fill="x")
        header.pack_propagate(False)

        for text, width in [
            ("", 3), ("Name", 18), ("Type", 6), ("Size", 8), ("Added", 10)
        ]:
            tk.Label(
                header,
                text=text,
                font=("Segoe UI", 9, "bold"),
                bg=COLOUR_ACCENT,
                fg=COLOUR_TEXT,
                width=width,
                anchor="w"
            ).pack(side="left", padx=6)

        canvas = tk.Canvas(
            self._list_frame,
            bg=COLOUR_BACKGROUND,
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            self._list_frame,
            orient="vertical",
            command=canvas.yview
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._list_inner = tk.Frame(canvas, bg=COLOUR_BACKGROUND)
        self._canvas_win = canvas.create_window(
            (0, 0), window=self._list_inner, anchor="nw"
        )
        self._list_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self._canvas_win, width=e.width)
        )

        self._enable_drag_drop(canvas)

    def _enable_drag_drop(self, canvas: tk.Canvas) -> None:
        """Enable drag-and-drop. Fails silently if unavailable."""
        try:
            canvas.drop_target_register("DND_Files")
            canvas.dnd_bind("<<Drop>>", self._handle_drop)
        except Exception:
            pass

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load_documents(self) -> None:
        """Load all documents and apply filters."""
        self._all_documents = load_all_documents()
        self._selected_ids.clear()
        self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply active filters and sort."""
        filter_type = self._active_filter

        self._filtered_docs = filter_documents(
            documents             = self._all_documents,
            query                 = self._search_query,
            category_id           = self._active_category,
            file_type             = filter_type if filter_type in ("pdf", "image") else None,
            uncategorized_only    = filter_type == "uncategorized",
            favorites_only        = filter_type == "favorites",
            recently_opened       = filter_type == "recent",
            expired_only          = filter_type == "expired",
            expiring_soon_only    = filter_type == "expiring_soon",
            integrity_issues_only = filter_type == "integrity_issues",
            sort_by               = self._sort_by,
            ascending             = self._ascending
        )
        self._render_list()

    def _render_list(self) -> None:
        """Render the filtered document list."""
        for widget in self._list_inner.winfo_children():
            widget.destroy()

        self._item_frames = {}
        self._update_toolbar_state()

        if not self._filtered_docs:
            self._render_empty_state()
            return

        for doc in self._filtered_docs:
            self._render_document_row(doc)

    def _render_empty_state(self) -> None:
        """Display empty state message."""
        tk.Label(
            self._list_inner,
            text="📂",
            font=("Segoe UI", 36),
            bg=COLOUR_BACKGROUND,
            fg=COLOUR_SUBTLE
        ).pack(pady=(60, 8))

        if self._search_query:
            msg = f"No results for \"{self._search_query}\""
            sub = "Try a different search term."
        elif self._active_filter == "favorites":
            msg = "No favorites yet."
            sub = "Click ☆ in the preview panel to mark a document."
        elif self._active_filter == "recent":
            msg = "No recently opened documents."
            sub = "Open a document to see it here."
        elif self._active_filter == "expired":
            msg = "No expired documents."
            sub = "Documents past their expiry date appear here."
        elif self._active_filter == "expiring_soon":
            msg = "No documents expiring soon."
            sub = "Documents expiring within 30 days appear here."
        elif self._active_filter == "integrity_issues":
            msg = "No integrity issues found."
            sub = "All documents have passed verification."
        elif self._active_filter not in (None, "all"):
            msg = "No documents match this filter."
            sub = "Try a different category or filter."
        else:
            msg = "No documents yet."
            sub = "Click  ＋ Import  to add your first document."

        tk.Label(
            self._list_inner,
            text=msg,
            font=("Segoe UI", 12, "bold"),
            bg=COLOUR_BACKGROUND,
            fg=COLOUR_TEXT
        ).pack()

        tk.Label(
            self._list_inner,
            text=sub,
            font=("Segoe UI", 10),
            bg=COLOUR_BACKGROUND,
            fg=COLOUR_SUBTLE
        ).pack(pady=(4, 0))

    def _render_document_row(self, document: Document) -> None:
        """Render a single document row with lifecycle indicators."""
        from modules.document_vault.core.lifecycle import is_expired, is_expiring_soon

        is_selected = document.id in self._selected_ids
        bg   = COLOUR_SELECTED if is_selected else COLOUR_ITEM_BG
        icon = FILE_ICONS.get(document.file_type.lower(), "📄")
        star = "⭐ " if document.is_favorite else ""

        lifecycle_indicator = ""
        if is_expired(document.expiry_date):
            lifecycle_indicator = " ❌"
        elif is_expiring_soon(document.expiry_date):
            lifecycle_indicator = " ⏰"
        elif document.integrity_status is False:
            lifecycle_indicator = " ⚠"

        row = tk.Frame(self._list_inner, bg=bg, cursor="hand2")
        row.pack(fill="x", padx=4, pady=2)

        tk.Label(
            row,
            text="✓" if is_selected else " ",
            font=("Segoe UI", 10, "bold"),
            bg=bg,
            fg=COLOUR_HIGHLIGHT if is_selected else bg,
            width=2
        ).pack(side="left", padx=(6, 2))

        tk.Label(
            row,
            text=icon,
            font=("Segoe UI", 12),
            bg=bg,
            fg=COLOUR_TEXT
        ).pack(side="left", padx=(4, 4), pady=10)

        tk.Label(
            row,
            text=f"{star}{document.original_name}{lifecycle_indicator}",
            font=("Segoe UI", 10),
            bg=bg,
            fg=COLOUR_TEXT,
            anchor="w"
        ).pack(side="left", fill="x", expand=True, pady=10)

        tk.Label(
            row,
            text=document.file_type.upper(),
            font=("Segoe UI", 8, "bold"),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            padx=5,
            pady=2
        ).pack(side="left", padx=5)

        tk.Label(
            row,
            text=document.formatted_size(),
            font=("Segoe UI", 9),
            bg=bg,
            fg=COLOUR_SUBTLE,
            width=8,
            anchor="e"
        ).pack(side="left", padx=4)

        tk.Label(
            row,
            text=document.date_added[:10],
            font=("Segoe UI", 9),
            bg=bg,
            fg=COLOUR_SUBTLE,
            width=10,
            anchor="e"
        ).pack(side="left", padx=(4, 10))

        all_widgets = [row] + list(row.winfo_children())
        for widget in all_widgets:
            widget.bind(
                "<Button-1>",
                lambda e, d=document, r=row: self._handle_row_click(d, r, e)
            )
            widget.bind(
                "<Control-Button-1>",
                lambda e, d=document, r=row: self._handle_ctrl_click(d, r)
            )

        if document.id is not None:
            self._item_frames[document.id] = row

    # ── Selection ─────────────────────────────────────────────────────────────

    def _handle_row_click(
        self,
        document: Document,
        row: tk.Frame,
        event: tk.Event
    ) -> None:
        """Handle single click selection."""
        self._selected_ids = {document.id}
        self._refresh_row_colours()
        self._update_toolbar_state()
        self._load_preview(document)

    def _handle_ctrl_click(
        self,
        document: Document,
        row: tk.Frame
    ) -> None:
        """Handle CTRL+Click multi-selection."""
        if document.id in self._selected_ids:
            self._selected_ids.discard(document.id)
        else:
            self._selected_ids.add(document.id)
        self._refresh_row_colours()
        self._update_toolbar_state()

        if len(self._selected_ids) == 1:
            doc = next(
                (d for d in self._filtered_docs if d.id in self._selected_ids),
                None
            )
            if doc:
                self._load_preview(doc)

    def _handle_select_all(self) -> None:
        """Select all documents in the filtered list."""
        self._selected_ids = {
            d.id for d in self._filtered_docs if d.id is not None
        }
        self._refresh_row_colours()
        self._update_toolbar_state()

    def _refresh_row_colours(self) -> None:
        """Update row highlight colours."""
        for doc_id, frame in self._item_frames.items():
            is_selected = doc_id in self._selected_ids
            bg = COLOUR_SELECTED if is_selected else COLOUR_ITEM_BG
            frame.config(bg=bg)
            for widget in frame.winfo_children():
                try:
                    if isinstance(widget, tk.Label) and widget.cget("text") in ("✓", " "):
                        widget.config(
                            bg=bg,
                            text="✓" if is_selected else " ",
                            fg=COLOUR_HIGHLIGHT if is_selected else bg
                        )
                    else:
                        widget.config(bg=bg)
                except Exception:
                    pass

    def _update_toolbar_state(self) -> None:
        """Update toolbar based on selection count."""
        count = len(self._selected_ids)
        if count == 0:
            self._toolbar.update_state("none")
        elif count == 1:
            self._toolbar.update_state("single", "1 document selected")
        else:
            self._toolbar.update_state("multi", f"{count} documents selected")

    def _load_preview(self, document: Document) -> None:
        """Decrypt and display a document preview."""
        encrypted_path  = VAULT_ENCRYPTED_PATH / document.encrypted_name
        decrypted_bytes = decrypt_file_to_memory(
            encrypted_path,
            self._master_password
        )
        self._preview_panel.show_document(document, decrypted_bytes)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _handle_filter_change(
        self,
        category_id: Optional[int],
        filter_type: Optional[str]
    ) -> None:
        """Handle sidebar navigation selection."""
        self._active_category = category_id
        self._active_filter   = filter_type
        self._search_query    = ""
        self._search_bar.clear()
        self._selected_ids.clear()
        self._preview_panel.clear()
        self._load_documents()

    def _handle_search(self, query: str) -> None:
        """Handle search bar input."""
        self._search_query = query
        self._apply_filters()

    def _handle_sort_change(self, sort_by: str, ascending: bool) -> None:
        """Handle sort change."""
        self._sort_by   = sort_by
        self._ascending = ascending
        self._apply_filters()

    def _handle_import(self) -> None:
        """Open file dialog and import."""
        file_path = open_file_dialog()
        if file_path is None:
            return
        self._import_file(file_path)

    def _handle_drop(self, event) -> None:
        """Handle drag-and-drop import."""
        raw   = event.data.strip()
        paths = self.tk.splitlist(raw)
        for path_str in paths:
            self._import_file(Path(path_str.strip("{}")))

    def _import_file(self, file_path: Path) -> None:
        """Execute the full import pipeline with duplicate detection."""
        is_valid, error = validate_file(file_path)
        if not is_valid:
            messagebox.showerror("Import Failed", error)
            return

        checksum = generate_checksum(file_path)

        if checksum:
            existing = get_document_by_checksum(checksum)
            if existing:
                choice = messagebox.askyesnocancel(
                    "Duplicate Detected",
                    f"This document appears to already exist:\n\n"
                    f"  {existing.original_name}\n\n"
                    f"Import anyway?"
                )
                if choice is None or not choice:
                    return

        try:
            document = extract_metadata(file_path)
        except Exception as error:
            messagebox.showerror(
                "Import Failed", f"Could not read file metadata.\n{error}"
            )
            return

        document.checksum = checksum

        encrypted_path = VAULT_ENCRYPTED_PATH / document.encrypted_name
        if not encrypt_file(file_path, encrypted_path, self._master_password):
            messagebox.showerror(
                "Import Failed", "Encryption failed. Document not imported."
            )
            return

        doc_id = insert_document(document)
        if doc_id is None:
            safe_delete_file(encrypted_path)
            messagebox.showerror(
                "Import Failed", "Database error. Document not imported."
            )
            return

        document.id = doc_id
        self._sidebar.refresh()
        self._load_documents()

    def _handle_single_delete(self) -> None:
        """Delete the single selected document."""
        if len(self._selected_ids) != 1:
            return
        doc_id = next(iter(self._selected_ids))
        doc    = next(
            (d for d in self._filtered_docs if d.id == doc_id), None
        )
        if doc is None:
            return

        confirmed = messagebox.askyesno(
            "Confirm Delete",
            f"Permanently delete '{doc.original_name}'?\n\nThis cannot be undone."
        )
        if not confirmed:
            return

        safe_delete_file(VAULT_ENCRYPTED_PATH / doc.encrypted_name)
        delete_document(doc.id)
        self._selected_ids.clear()
        self._preview_panel.clear()
        self._sidebar.refresh()
        self._load_documents()

    def _handle_rename_selected(self) -> None:
        """Open preview panel for rename."""
        if len(self._selected_ids) != 1:
            return
        doc_id = next(iter(self._selected_ids))
        doc    = next(
            (d for d in self._filtered_docs if d.id == doc_id), None
        )
        if doc:
            self._load_preview(doc)

    def _handle_toggle_favorite_selected(self) -> None:
        """Open preview panel for favorite toggle."""
        if len(self._selected_ids) != 1:
            return
        doc_id = next(iter(self._selected_ids))
        doc    = next(
            (d for d in self._filtered_docs if d.id == doc_id), None
        )
        if doc:
            self._load_preview(doc)

    def _handle_bulk_delete(self) -> None:
        """Delete all selected documents."""
        count = len(self._selected_ids)
        if count == 0:
            return

        confirmed = messagebox.askyesno(
            "Confirm Bulk Delete",
            f"Permanently delete {count} selected documents?\n\nThis cannot be undone."
        )
        if not confirmed:
            return

        docs_to_delete = [
            d for d in self._filtered_docs if d.id in self._selected_ids
        ]
        for doc in docs_to_delete:
            safe_delete_file(VAULT_ENCRYPTED_PATH / doc.encrypted_name)

        deleted = bulk_delete_documents(list(self._selected_ids))
        self._selected_ids.clear()
        self._preview_panel.clear()
        self._sidebar.refresh()
        self._load_documents()
        messagebox.showinfo("Bulk Delete", f"{deleted} document(s) deleted.")

    def _handle_bulk_category(self) -> None:
        """Assign category to all selected documents."""
        if not self._selected_ids:
            return

        categories = load_all_categories()
        if not categories:
            messagebox.showinfo(
                "No Categories",
                "No categories available. Create one in the sidebar first."
            )
            return

        options = ["Uncategorized"] + [c.name for c in categories]
        choice  = simpledialog.askstring(
            "Assign Category",
            f"Category for {len(self._selected_ids)} documents:\n"
            f"Options: {', '.join(options)}"
        )
        if not choice:
            return

        category_id: Optional[int] = None
        for cat in categories:
            if cat.name.lower() == choice.strip().lower():
                category_id = cat.id
                break

        updated = bulk_set_category(list(self._selected_ids), category_id)
        self._sidebar.refresh()
        self._load_documents()
        messagebox.showinfo(
            "Category Updated", f"Category updated for {updated} document(s)."
        )

    def _handle_bulk_favorite(self) -> None:
        """Mark all selected documents as favorites."""
        if not self._selected_ids:
            return
        updated = bulk_set_favorite(list(self._selected_ids), True)
        self._sidebar.refresh()
        self._load_documents()
        messagebox.showinfo(
            "Favorites Updated", f"{updated} document(s) added to favorites."
        )

    def _handle_export_selected(self) -> None:
        """Export all selected documents."""
        from modules.document_vault.ui.export_dialog import export_selected_documents
        selected_docs = [
            d for d in self._filtered_docs
            if d.id in self._selected_ids
        ]
        if not selected_docs:
            return
        export_selected_documents(self, selected_docs, self._master_password)

    def _handle_export_vault(self) -> None:
        """Export the entire vault."""
        from modules.document_vault.ui.export_dialog import export_entire_vault
        export_entire_vault(
            self,
            self._master_password,
            len(self._all_documents)
        )

    def _handle_lock(self) -> None:
        """Lock the vault."""
        self._vault_state.lock()
        self._on_lock()

    def _on_metadata_saved(self) -> None:
        """Refresh after metadata save."""
        self._sidebar.refresh()
        self._load_documents()




