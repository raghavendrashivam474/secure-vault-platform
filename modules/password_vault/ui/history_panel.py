"""
modules/password_vault/ui/history_panel.py

Password history viewer with restore capability.
"""

import tkinter as tk
from typing import Callable

from vaultcore.theme import Theme
from vaultcore.event_bus import platform_bus

from modules.password_vault.models.password_entry import PasswordEntry
from modules.password_vault.models.password_history import PasswordHistoryRecord
from modules.password_vault.core.history import (
    get_history_for_entry, get_history_record, add_history_record
)
from modules.password_vault.core.database import update_password
from modules.password_vault.ui.password_editor import decrypt_file_to_memory_string


class HistoryPanel(tk.Toplevel):
    """
    Password history timeline for a specific entry.

    Shows metadata only. Historical passwords remain encrypted.
    Restoring preserves the currently-active password as a new history entry.
    """

    def __init__(
        self,
        parent: tk.Widget,
        entry: PasswordEntry,
        master_password: str,
        dialogs,
        notifications,
        activity_service,
        on_restored: Callable
    ) -> None:
        super().__init__(parent)
        self.title(f"Password History — {entry.title}")
        self.geometry("560x520")
        self.configure(bg=Theme.BACKGROUND)
        self.grab_set()

        self._entry            = entry
        self._master_password  = master_password
        self._dialogs          = dialogs
        self._notifications    = notifications
        self._activity_service = activity_service
        self._on_restored      = on_restored

        self._build()
        self._render()

    def _build(self) -> None:
        tk.Label(
            self,
            text=f"🕒  Password History",
            font=Theme.FONT_HEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(pady=(20, 4))

        tk.Label(
            self,
            text=f"for {self._entry.title}",
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(pady=(0, 16))

        canvas = tk.Canvas(self, bg=Theme.BACKGROUND, highlightthickness=0)
        sb     = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        self._body = tk.Frame(canvas, bg=Theme.BACKGROUND)
        win = canvas.create_window((0, 0), window=self._body, anchor="nw")
        self._body.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width)
        )

    def _render(self) -> None:
        for widget in self._body.winfo_children():
            widget.destroy()

        # Show current password first
        current_frame = tk.Frame(self._body, bg=Theme.ACCENT, padx=16, pady=12)
        current_frame.pack(fill="x", pady=(0, 8))

        tk.Label(
            current_frame,
            text="●  Current Password",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.ACCENT,
            fg=Theme.SUCCESS
        ).pack(anchor="w")

        current_date = (self._entry.password_changed_at or self._entry.modified_at or "")[:19].replace("T", " ")
        tk.Label(
            current_frame,
            text=f"Set: {current_date}",
            font=Theme.FONT_SMALL,
            bg=Theme.ACCENT,
            fg=Theme.SUBTLE
        ).pack(anchor="w")

        tk.Label(
            current_frame,
            text=f"Strength: {self._entry.strength_label()} ({self._entry.strength_score}/100)",
            font=Theme.FONT_SMALL,
            bg=Theme.ACCENT,
            fg=Theme.SUBTLE
        ).pack(anchor="w")

        # History records
        records = get_history_for_entry(self._entry.id)

        if not records:
            tk.Label(
                self._body,
                text="No password history yet.",
                font=Theme.FONT_BODY,
                bg=Theme.BACKGROUND,
                fg=Theme.SUBTLE
            ).pack(pady=20)
            return

        tk.Label(
            self._body,
            text=f"Previous Versions ({len(records)})",
            font=Theme.FONT_LABEL,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(12, 8))

        for record in records:
            self._render_record(record)

    def _render_record(self, record: PasswordHistoryRecord) -> None:
        row = tk.Frame(self._body, bg=Theme.PANEL, padx=16, pady=10)
        row.pack(fill="x", pady=4)

        left = tk.Frame(row, bg=Theme.PANEL)
        left.pack(side="left", fill="x", expand=True)

        changed_at = record.changed_at[:19].replace("T", " ")
        tk.Label(
            left,
            text=f"Replaced: {changed_at}",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(anchor="w")

        # Strength label
        if record.strength_score >= 80:
            strength_label, colour = "Very Strong", Theme.SUCCESS
        elif record.strength_score >= 60:
            strength_label, colour = "Strong", Theme.SUCCESS
        elif record.strength_score >= 40:
            strength_label, colour = "Fair", Theme.WARNING
        else:
            strength_label, colour = "Weak", Theme.ERROR

        tk.Label(
            left,
            text=f"● {strength_label} ({record.strength_score}/100)  •  {record.reason}",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=colour
        ).pack(anchor="w", pady=(2, 0))

        tk.Button(
            row,
            text="↺  Restore",
            font=Theme.FONT_SMALL,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=lambda r=record: self._handle_restore(r)
        ).pack(side="right")

    def _handle_restore(self, record: PasswordHistoryRecord) -> None:
        """
        Restore a historical password.
        The current password becomes a new history record.
        """
        if not self._dialogs.confirm_destructive(
            "Restore Password",
            f"Restore this historical version?\n\n"
            f"Your current password will be moved to history."
        ):
            return

        # Verify the historical password can be decrypted
        historical_plaintext = decrypt_file_to_memory_string(
            record.password_encrypted, self._master_password
        )
        if not historical_plaintext:
            self._notifications.error("Failed to decrypt historical password.")
            return

        # Save current password to history first
        add_history_record(
            entry_id           = self._entry.id,
            password_encrypted = self._entry.password_encrypted,
            strength_score     = self._entry.strength_score,
            reason             = "restore"
        )

        # Restore historical password
        self._entry.password_encrypted = record.password_encrypted
        self._entry.strength_score     = record.strength_score
        update_password(self._entry, password_changed=True)

        # Publish domain event
        platform_bus.publish("password.history_restored", {
            "entry_id":   self._entry.id,
            "title":      self._entry.title,
            "history_id": record.id
        })

        self._activity_service.record(
            "PasswordRestored", "password_vault", self._entry.title
        )
        self._notifications.success("Password restored from history.")

        self._on_restored()
        self._render()
