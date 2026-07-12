"""
modules/password_vault/ui/recovery_dialog.py

Recovery import preview dialog.
"""

import tkinter as tk
from typing import Callable

from vaultcore.theme import Theme

from modules.password_vault.core.vault_import import RecoveryPreview


class RecoveryPreviewDialog(tk.Toplevel):
    """
    Preview a .pvexport package before restoring.
    """

    def __init__(
        self,
        parent: tk.Widget,
        preview: RecoveryPreview,
        on_confirm: Callable[[bool], None]
    ) -> None:
        super().__init__(parent)
        self.title("Recovery Import Preview")
        self.geometry("560x460")
        self.configure(bg=Theme.BACKGROUND)
        self.grab_set()

        self._preview    = preview
        self._on_confirm = on_confirm
        self._build()

    def _build(self) -> None:
        # Header
        tk.Label(
            self,
            text="🔄  Recovery Import",
            font=Theme.FONT_HEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(pady=(20, 8))

        tk.Label(
            self,
            text="Package validated successfully.",
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND,
            fg=Theme.SUCCESS
        ).pack(pady=(0, 20))

        # Package details
        details = tk.Frame(self, bg=Theme.PANEL, padx=20, pady=16)
        details.pack(fill="x", padx=24)

        rows = [
            ("Format Version",  self._preview.format_version),
            ("Module Version",  self._preview.module_version),
            ("Exported",        self._preview.exported_at[:19].replace("T", " ")),
            ("Entries",         str(self._preview.entry_count)),
            ("History Records", str(self._preview.history_count)),
        ]

        for label, value in rows:
            row = tk.Frame(details, bg=Theme.PANEL)
            row.pack(fill="x", pady=3)

            tk.Label(
                row,
                text=label,
                font=Theme.FONT_LABEL,
                bg=Theme.PANEL,
                fg=Theme.SUBTLE,
                width=16,
                anchor="w"
            ).pack(side="left")

            tk.Label(
                row,
                text=value,
                font=Theme.FONT_BODY,
                bg=Theme.PANEL,
                fg=Theme.TEXT
            ).pack(side="left")

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
        ).pack(anchor="w", padx=24, pady=(20, 8))

        tk.Label(
            self,
            text="Recovery will add entries to your existing vault.\n"
                 "Your current data will not be replaced or lost.",
            font=Theme.FONT_SMALL,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE,
            justify="left"
        ).pack(anchor="w", padx=24, pady=(0, 20))

        # Buttons
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
            text=f"✓  Restore {self._preview.entry_count} Entries",
            font=Theme.FONT_BUTTON,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._handle_confirm
        ).pack(side="right")

    def _handle_confirm(self) -> None:
        """Confirm the restore."""
        skip_duplicates = self._skip_dupes_var.get()
        self._on_confirm(skip_duplicates)
        self.destroy()
