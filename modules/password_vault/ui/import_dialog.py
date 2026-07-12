"""
modules/password_vault/ui/import_dialog.py

CSV import preview and confirmation dialog.
"""

import tkinter as tk
from typing import Callable

from vaultcore.theme import Theme

from modules.password_vault.core.csv_import import ImportRow, ImportReport


class ImportPreviewDialog(tk.Toplevel):
    """
    Shows CSV import preview and lets user confirm.
    """

    def __init__(
        self,
        parent: tk.Widget,
        rows: list[ImportRow],
        on_confirm: Callable[[list[ImportRow], bool], None]
    ) -> None:
        """
        Initialize the preview dialog.

        Args:
            parent:     The parent widget.
            rows:       Parsed CSV rows.
            on_confirm: Callback(rows, skip_duplicates).
        """
        super().__init__(parent)
        self.title("CSV Import Preview")
        self.geometry("780x560")
        self.configure(bg=Theme.BACKGROUND)
        self.grab_set()

        self._rows       = rows
        self._on_confirm = on_confirm
        self._build()

    def _build(self) -> None:
        # Header
        tk.Label(
            self,
            text="📥  Import Preview",
            font=Theme.FONT_HEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(pady=(20, 8))

        # Summary
        valid      = len([r for r in self._rows if r.is_valid])
        invalid    = len([r for r in self._rows if not r.is_valid])
        duplicates = len([r for r in self._rows if r.is_duplicate])

        summary_frame = tk.Frame(self, bg=Theme.PANEL, padx=16, pady=12)
        summary_frame.pack(fill="x", padx=24, pady=(0, 12))

        summary_text = (
            f"Total rows: {len(self._rows)}   •   "
            f"Valid: {valid}   •   "
            f"Duplicates: {duplicates}   •   "
            f"Invalid: {invalid}"
        )

        tk.Label(
            summary_frame,
            text=summary_text,
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack()

        # Skip duplicates checkbox
        self._skip_dupes_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            self,
            text="Skip duplicates (recommended)",
            variable=self._skip_dupes_var,
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT,
            activebackground=Theme.BACKGROUND,
            selectcolor=Theme.ACCENT
        ).pack(anchor="w", padx=24, pady=(0, 12))

        # Row list
        list_frame = tk.Frame(self, bg=Theme.BACKGROUND)
        list_frame.pack(fill="both", expand=True, padx=24)

        canvas = tk.Canvas(list_frame, bg=Theme.BACKGROUND, highlightthickness=0)
        sb     = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        rows_container = tk.Frame(canvas, bg=Theme.BACKGROUND)
        win = canvas.create_window((0, 0), window=rows_container, anchor="nw")
        rows_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width)
        )

        for row in self._rows[:100]:  # Show first 100
            self._render_row(rows_container, row)

        if len(self._rows) > 100:
            tk.Label(
                rows_container,
                text=f"...and {len(self._rows) - 100} more rows",
                font=Theme.FONT_SMALL,
                bg=Theme.BACKGROUND,
                fg=Theme.SUBTLE
            ).pack(pady=8)

        # Action buttons
        button_frame = tk.Frame(self, bg=Theme.BACKGROUND)
        button_frame.pack(fill="x", padx=24, pady=16)

        tk.Button(
            button_frame,
            text="Cancel",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE,
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.destroy
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            button_frame,
            text=f"✓  Import {valid} Entries",
            font=Theme.FONT_BUTTON,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._handle_confirm
        ).pack(side="right")

    def _render_row(self, parent: tk.Widget, row: ImportRow) -> None:
        """Render a single row preview."""
        if not row.is_valid:
            bg = "#3a1a1a"
            status = f"⚠ {row.error}"
            status_color = Theme.ERROR
        elif row.is_duplicate:
            bg = "#3a3a1a"
            status = "⚠ Duplicate"
            status_color = Theme.WARNING
        else:
            bg = Theme.PANEL
            status = "✓ New"
            status_color = Theme.SUCCESS

        frame = tk.Frame(parent, bg=bg, padx=12, pady=6)
        frame.pack(fill="x", pady=1)

        left = tk.Frame(frame, bg=bg)
        left.pack(side="left", fill="x", expand=True)

        tk.Label(
            left,
            text=row.title or "(untitled)",
            font=Theme.FONT_BODY,
            bg=bg,
            fg=Theme.TEXT,
            anchor="w"
        ).pack(anchor="w")

        detail = f"{row.username}"
        if row.url:
            detail += f"  •  {row.url}"

        tk.Label(
            left,
            text=detail,
            font=Theme.FONT_SMALL,
            bg=bg,
            fg=Theme.SUBTLE,
            anchor="w"
        ).pack(anchor="w")

        tk.Label(
            frame,
            text=status,
            font=Theme.FONT_SMALL,
            bg=bg,
            fg=status_color
        ).pack(side="right")

    def _handle_confirm(self) -> None:
        """Confirm the import."""
        skip_dupes = self._skip_dupes_var.get()
        self._on_confirm(self._rows, skip_dupes)
        self.destroy()
