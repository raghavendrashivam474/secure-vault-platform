"""
ui/preview_panel.py

Enhanced preview panel for the Personal Document Vault.
Updated in Sprint 6 to display integrity status,
expiry information, and reminder toggle.
"""

import io
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable
from datetime import date

from PIL import Image, ImageTk
import fitz

from modules.document_vault.models.document import Document
from modules.document_vault.models.category import Category
from vaultcore.database import (
    update_document_metadata,
    load_all_categories,
    rename_document,
    toggle_favorite,
    update_document_last_opened,
    update_integrity_status
)
from modules.document_vault.core.integrity import verify_document_integrity
from modules.document_vault.core.lifecycle import get_expiry_status_label, is_expired, is_expiring_soon
from vaultcore.file_utils import validate_display_name, VAULT_ENCRYPTED_PATH
from pathlib import Path
from datetime import datetime, timezone


COLOUR_PANEL      = "#16213e"
COLOUR_ACCENT     = "#0f3460"
COLOUR_HIGHLIGHT  = "#e94560"
COLOUR_TEXT       = "#eaeaea"
COLOUR_SUBTLE     = "#a0a0b0"
COLOUR_ENTRY_BG   = "#0d1b2a"
COLOUR_SUCCESS    = "#51cf66"
COLOUR_ERROR      = "#ff6b6b"
COLOUR_WARNING    = "#ffd43b"

MAX_PREVIEW_WIDTH:  int = 440
MAX_PREVIEW_HEIGHT: int = 300


class PreviewPanel(tk.Frame):
    """
    Right-hand panel showing preview, metadata, integrity,
    expiry tracking, notes, and category assignment.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_metadata_saved: Optional[Callable] = None
    ) -> None:
        """
        Initialize the preview panel.

        Args:
            parent:            The parent widget.
            on_metadata_saved: Callback after any metadata save.
        """
        super().__init__(parent, bg=COLOUR_PANEL, width=480)
        self.pack_propagate(False)
        self._photo_reference:   Optional[ImageTk.PhotoImage] = None
        self._current_document:  Optional[Document] = None
        self._on_metadata_saved = on_metadata_saved
        self._categories:        list[Category] = []
        self._master_password:   str = ""
        self._build_empty()

    def set_master_password(self, password: str) -> None:
        """
        Set the master password for integrity verification.

        Args:
            password: The current session master password.
        """
        self._master_password = password

    def _build_empty(self) -> None:
        """Show empty state."""
        for widget in self.winfo_children():
            widget.destroy()
        tk.Label(
            self,
            text="Select a document\nto preview it",
            font=("Segoe UI", 11),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE,
            justify="center"
        ).place(relx=0.5, rely=0.5, anchor="center")

    def show_document(
        self,
        document: Document,
        decrypted_bytes: Optional[bytes]
    ) -> None:
        """
        Display document preview and metadata.

        Args:
            document:        The Document to display.
            decrypted_bytes: Decrypted bytes in memory.
        """
        self._current_document = document
        self._categories = load_all_categories()

        if document.id is not None:
            update_document_last_opened(document.id)

        self._rebuild(document, decrypted_bytes)

    def clear(self) -> None:
        """Reset to empty state."""
        self._current_document = None
        self._photo_reference  = None
        self._build_empty()

    def _rebuild(
        self,
        document: Document,
        decrypted_bytes: Optional[bytes]
    ) -> None:
        """Rebuild full panel content."""
        for widget in self.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(self, bg=COLOUR_PANEL, highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=COLOUR_PANEL)
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width)
        )

        pad = {"padx": 16}

        # ── Title and favorite ────────────────────────────────────────────────
        title_row = tk.Frame(inner, bg=COLOUR_PANEL)
        title_row.pack(fill="x", pady=(16, 4), **pad)

        star = "⭐" if document.is_favorite else "☆"
        self._fav_btn = tk.Button(
            title_row,
            text=star,
            font=("Segoe UI", 14),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_PANEL,
            relief="flat",
            cursor="hand2",
            command=self._handle_toggle_favorite
        )
        self._fav_btn.pack(side="left", padx=(0, 8))

        tk.Label(
            title_row,
            text=document.original_name,
            font=("Segoe UI", 11, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT,
            wraplength=360,
            justify="left"
        ).pack(side="left", fill="x", expand=True)

        # ── Rename ────────────────────────────────────────────────────────────
        rename_row = tk.Frame(inner, bg=COLOUR_PANEL)
        rename_row.pack(fill="x", pady=(0, 4), **pad)

        self._rename_entry = tk.Entry(
            rename_row,
            font=("Segoe UI", 10),
            bg=COLOUR_ENTRY_BG,
            fg=COLOUR_TEXT,
            insertbackground=COLOUR_TEXT,
            relief="flat",
            bd=6
        )
        ext  = Path(document.original_name).suffix
        stem = Path(document.original_name).stem
        self._rename_entry.insert(0, stem)
        self._rename_entry.pack(side="left", fill="x", expand=True, ipady=3)

        tk.Button(
            rename_row,
            text="Rename",
            font=("Segoe UI", 9),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda e=ext: self._handle_rename(e)
        ).pack(side="left", padx=(6, 0))

        self._rename_entry.bind(
            "<Return>",
            lambda event, e=ext: self._handle_rename(e)
        )

        # ── Status label ──────────────────────────────────────────────────────
        self._status_label = tk.Label(
            inner,
            text="",
            font=("Segoe UI", 9),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUCCESS
        )
        self._status_label.pack(anchor="w", **pad)

        tk.Frame(inner, bg=COLOUR_ACCENT, height=1).pack(
            fill="x", **pad, pady=(4, 0)
        )

        # ── Preview image ─────────────────────────────────────────────────────
        self._preview_label = tk.Label(inner, bg=COLOUR_PANEL)
        self._preview_label.pack(pady=12, **pad)

        if decrypted_bytes:
            if document.mime_type == "application/pdf":
                self._render_pdf(decrypted_bytes)
            elif document.mime_type.startswith("image/"):
                self._render_image(decrypted_bytes)
        else:
            self._preview_label.config(
                text="⚠  Preview unavailable",
                fg=COLOUR_HIGHLIGHT,
                font=("Segoe UI", 10)
            )

        tk.Frame(inner, bg=COLOUR_ACCENT, height=1).pack(fill="x", **pad)

        # ── Integrity status ──────────────────────────────────────────────────
        self._section_label(inner, "INTEGRITY")

        integrity_colour = COLOUR_SUBTLE
        if document.integrity_status is True:
            integrity_colour = COLOUR_SUCCESS
        elif document.integrity_status is False:
            integrity_colour = COLOUR_ERROR

        integrity_row = tk.Frame(inner, bg=COLOUR_PANEL)
        integrity_row.pack(fill="x", pady=(0, 4), **pad)

        tk.Label(
            integrity_row,
            text=document.integrity_label(),
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_PANEL,
            fg=integrity_colour
        ).pack(side="left")

        if document.verified_at:
            tk.Label(
                integrity_row,
                text=f"  (checked {document.verified_at[:10]})",
                font=("Segoe UI", 9),
                bg=COLOUR_PANEL,
                fg=COLOUR_SUBTLE
            ).pack(side="left")

        tk.Button(
            inner,
            text="Verify Now",
            font=("Segoe UI", 9),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._handle_verify_integrity
        ).pack(anchor="w", **pad, pady=(0, 8))

        tk.Frame(inner, bg=COLOUR_ACCENT, height=1).pack(fill="x", **pad)

        # ── Details ───────────────────────────────────────────────────────────
        self._section_label(inner, "DETAILS")
        for label, value in [
            ("Added",    document.date_added[:10]),
            ("Modified", document.last_modified[:10]),
            ("Opened",   (document.last_opened_at or "Never")[:10]),
            ("Size",     document.formatted_size()),
            ("Type",     document.file_type.upper()),
        ]:
            self._meta_row(inner, label, value, pad)

        # ── Checksum ──────────────────────────────────────────────────────────
        if document.checksum:
            tk.Label(
                inner,
                text="SHA-256",
                font=("Segoe UI", 8, "bold"),
                bg=COLOUR_PANEL,
                fg=COLOUR_SUBTLE
            ).pack(anchor="w", **pad, pady=(8, 2))

            tk.Label(
                inner,
                text=document.checksum[:32] + "...",
                font=("Courier New", 8),
                bg=COLOUR_PANEL,
                fg=COLOUR_SUBTLE,
                anchor="w"
            ).pack(fill="x", **pad)

        tk.Frame(inner, bg=COLOUR_ACCENT, height=1).pack(
            fill="x", **pad, pady=(10, 0)
        )

        # ── Expiry tracking ───────────────────────────────────────────────────
        self._section_label(inner, "EXPIRY")

        expiry_status = get_expiry_status_label(document.expiry_date)
        expiry_colour = COLOUR_TEXT

        if is_expired(document.expiry_date):
            expiry_colour = COLOUR_ERROR
        elif is_expiring_soon(document.expiry_date):
            expiry_colour = COLOUR_WARNING

        tk.Label(
            inner,
            text=expiry_status,
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_PANEL,
            fg=expiry_colour
        ).pack(anchor="w", **pad, pady=(0, 6))

        expiry_row = tk.Frame(inner, bg=COLOUR_PANEL)
        expiry_row.pack(fill="x", **pad, pady=(0, 4))

        tk.Label(
            expiry_row,
            text="Expiry Date",
            font=("Segoe UI", 9, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE,
            width=12,
            anchor="w"
        ).pack(side="left")

        self._expiry_entry = tk.Entry(
            expiry_row,
            font=("Segoe UI", 10),
            bg=COLOUR_ENTRY_BG,
            fg=COLOUR_TEXT,
            insertbackground=COLOUR_TEXT,
            relief="flat",
            bd=6,
            width=14
        )
        if document.expiry_date:
            self._expiry_entry.insert(0, document.expiry_date)
        else:
            self._expiry_entry.insert(0, "YYYY-MM-DD")
        self._expiry_entry.pack(side="left", ipady=3)

        self._reminder_var = tk.BooleanVar(value=document.reminder_enabled)
        tk.Checkbutton(
            inner,
            text="Enable expiry reminder",
            variable=self._reminder_var,
            font=("Segoe UI", 10),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_PANEL,
            selectcolor=COLOUR_ACCENT
        ).pack(anchor="w", **pad, pady=(0, 4))

        tk.Frame(inner, bg=COLOUR_ACCENT, height=1).pack(
            fill="x", **pad, pady=(4, 0)
        )

        # ── Category ──────────────────────────────────────────────────────────
        self._section_label(inner, "CATEGORY")
        options = ["Uncategorized"] + [c.name for c in self._categories]
        self._category_var = tk.StringVar()
        current = "Uncategorized"
        if document.category_id is not None:
            for cat in self._categories:
                if cat.id == document.category_id:
                    current = cat.name
                    break
        self._category_var.set(current)

        dd = tk.OptionMenu(inner, self._category_var, *options)
        dd.config(
            font=("Segoe UI", 10),
            bg=COLOUR_ENTRY_BG,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_ACCENT,
            activeforeground=COLOUR_TEXT,
            highlightthickness=0,
            relief="flat"
        )
        dd["menu"].config(
            bg=COLOUR_ACCENT, fg=COLOUR_TEXT, font=("Segoe UI", 10)
        )
        dd.pack(fill="x", **pad)

        tk.Frame(inner, bg=COLOUR_ACCENT, height=1).pack(
            fill="x", **pad, pady=(10, 0)
        )

        # ── Notes ─────────────────────────────────────────────────────────────
        self._section_label(inner, "NOTES")
        self._notes_text = tk.Text(
            inner,
            font=("Segoe UI", 10),
            bg=COLOUR_ENTRY_BG,
            fg=COLOUR_TEXT,
            insertbackground=COLOUR_TEXT,
            relief="flat",
            bd=8,
            height=4,
            wrap="word"
        )
        self._notes_text.pack(fill="x", **pad)
        if document.notes:
            self._notes_text.insert("1.0", document.notes)

        tk.Button(
            inner,
            text="Save Changes",
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_HIGHLIGHT,
            fg="#ffffff",
            activebackground=COLOUR_ACCENT,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._handle_save
        ).pack(anchor="w", pady=(8, 24), **pad)

    def _section_label(self, parent: tk.Widget, text: str) -> None:
        """Render a section header."""
        tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 8, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(anchor="w", padx=16, pady=(12, 6))

    def _meta_row(
        self,
        parent: tk.Widget,
        label: str,
        value: str,
        pad: dict
    ) -> None:
        """Render a single metadata key-value row."""
        row = tk.Frame(parent, bg=COLOUR_PANEL)
        row.pack(fill="x", pady=2, **pad)
        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE,
            width=9,
            anchor="w"
        ).pack(side="left")
        tk.Label(
            row,
            text=value,
            font=("Segoe UI", 9),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT,
            anchor="w"
        ).pack(side="left")

    def _handle_verify_integrity(self) -> None:
        """Run integrity verification on the current document."""
        if self._current_document is None:
            return

        self._status_label.config(
            text="Verifying...", fg=COLOUR_SUBTLE
        )
        self.update()

        is_valid, message = verify_document_integrity(
            self._current_document.encrypted_name,
            self._current_document.checksum,
            self._master_password
        )

        now = datetime.now(timezone.utc).isoformat()
        update_integrity_status(self._current_document.id, is_valid, now)
        self._current_document.integrity_status = is_valid
        self._current_document.verified_at      = now

        colour = COLOUR_SUCCESS if is_valid else COLOUR_ERROR
        self._status_label.config(
            text=f"{'✓' if is_valid else '⚠'}  {message}",
            fg=colour
        )

        if self._on_metadata_saved:
            self._on_metadata_saved()

    def _handle_toggle_favorite(self) -> None:
        """Toggle the favorite status."""
        if self._current_document is None:
            return
        new_state = not self._current_document.is_favorite
        success   = toggle_favorite(self._current_document.id, new_state)
        if success:
            self._current_document.is_favorite = new_state
            self._fav_btn.config(text="⭐" if new_state else "☆")
            self._status_label.config(
                text="Added to favorites." if new_state else "Removed from favorites.",
                fg=COLOUR_SUCCESS
            )
            if self._on_metadata_saved:
                self._on_metadata_saved()

    def _handle_rename(self, extension: str) -> None:
        """Validate and save a document rename."""
        if self._current_document is None:
            return
        stem     = self._rename_entry.get().strip()
        is_valid, error = validate_display_name(stem, extension)
        if not is_valid:
            self._status_label.config(text=f"⚠ {error}", fg=COLOUR_ERROR)
            return
        new_name = stem + extension
        success  = rename_document(self._current_document.id, new_name)
        if success:
            self._current_document.original_name = new_name
            self._status_label.config(
                text="✓ Renamed successfully.", fg=COLOUR_SUCCESS
            )
            if self._on_metadata_saved:
                self._on_metadata_saved()
        else:
            self._status_label.config(text="⚠ Rename failed.", fg=COLOUR_ERROR)

    def _handle_save(self) -> None:
        """Save notes, category, expiry, and reminder changes."""
        if self._current_document is None:
            return

        notes    = self._notes_text.get("1.0", "end-1c").strip() or None
        selected = self._category_var.get()
        category_id: Optional[int] = None
        for cat in self._categories:
            if cat.name == selected:
                category_id = cat.id
                break

        expiry_input = self._expiry_entry.get().strip()
        expiry_date: Optional[str] = None
        if expiry_input and expiry_input != "YYYY-MM-DD":
            try:
                from datetime import date as date_type
                date_type.fromisoformat(expiry_input)
                expiry_date = expiry_input
            except ValueError:
                self._status_label.config(
                    text="⚠ Invalid date. Use YYYY-MM-DD format.",
                    fg=COLOUR_ERROR
                )
                return

        reminder = self._reminder_var.get()

        success = update_document_metadata(
            self._current_document.id,
            notes,
            category_id,
            expiry_date,
            reminder
        )

        if success:
            self._current_document.notes            = notes
            self._current_document.category_id      = category_id
            self._current_document.expiry_date       = expiry_date
            self._current_document.reminder_enabled  = reminder
            self._status_label.config(
                text="✓ Changes saved.", fg=COLOUR_SUCCESS
            )
            if self._on_metadata_saved:
                self._on_metadata_saved()
        else:
            self._status_label.config(
                text="⚠ Failed to save.", fg=COLOUR_ERROR
            )

    def _render_pdf(self, data: bytes) -> None:
        """Render the first PDF page."""
        try:
            pdf    = fitz.open(stream=data, filetype="pdf")
            page   = pdf[0]
            matrix = fitz.Matrix(1.3, 1.3)
            pixmap = page.get_pixmap(matrix=matrix)
            image  = Image.frombytes(
                "RGB", [pixmap.width, pixmap.height], pixmap.samples
            )
            image.thumbnail(
                (MAX_PREVIEW_WIDTH, MAX_PREVIEW_HEIGHT), Image.LANCZOS
            )
            photo = ImageTk.PhotoImage(image)
            self._photo_reference = photo
            self._preview_label.config(image=photo, text="")
            pdf.close()
        except Exception as error:
            print(f"[PreviewPanel] PDF error: {error}")
            self._preview_label.config(
                text="PDF preview unavailable",
                fg=COLOUR_SUBTLE,
                font=("Segoe UI", 10)
            )

    def _render_image(self, data: bytes) -> None:
        """Render an image from bytes."""
        try:
            image = Image.open(io.BytesIO(data))
            image.thumbnail(
                (MAX_PREVIEW_WIDTH, MAX_PREVIEW_HEIGHT), Image.LANCZOS
            )
            photo = ImageTk.PhotoImage(image)
            self._photo_reference = photo
            self._preview_label.config(image=photo, text="")
        except Exception as error:
            print(f"[PreviewPanel] Image error: {error}")
            self._preview_label.config(
                text="Image preview unavailable",
                fg=COLOUR_SUBTLE,
                font=("Segoe UI", 10)
            )

