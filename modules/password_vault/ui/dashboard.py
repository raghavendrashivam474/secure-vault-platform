"""
modules/password_vault/ui/dashboard.py

Password Vault dashboard - main UI.
"""

import tkinter as tk
from typing import Callable, Optional

from vaultcore.theme import Theme
from vaultcore.event_bus import platform_bus, Events

from modules.password_vault.models.password_entry import PasswordEntry
from modules.password_vault.core.database import (
    load_all_passwords, delete_password,
    update_last_accessed, get_password_statistics, toggle_favorite
)
from modules.password_vault.ui.password_editor import (
    PasswordEditor, decrypt_file_to_memory_string
)


STRENGTH_COLOURS = {
    "Very Strong": Theme.SUCCESS,
    "Strong":      Theme.SUCCESS,
    "Fair":        Theme.WARNING,
    "Weak":        Theme.ERROR,
}


class PasswordVaultDashboard(tk.Frame):
    """
    Main Password Vault dashboard.

    Uses all VaultCore platform services:
      - Clipboard Manager
      - Dialog Framework
      - Notification Center
      - Activity Service
      - Recent Items
    """

    def __init__(
        self,
        parent: tk.Widget,
        master_password: str,
        clipboard,
        dialogs,
        notifications,
        notification_center,
        activity_service,
        recent_items,
        on_close: Callable
    ) -> None:
        super().__init__(parent, bg=Theme.BACKGROUND)
        self._master_password     = master_password
        self._clipboard           = clipboard
        self._dialogs             = dialogs
        self._notifications       = notifications
        self._notification_center = notification_center
        self._activity_service    = activity_service
        self._recent_items        = recent_items
        self._on_close            = on_close

        self._passwords: list[PasswordEntry] = []
        self._selected_entry: Optional[PasswordEntry] = None
        self._search_query: str = ""

        self._build()
        self._load_data()

    def _build(self) -> None:
        """Construct the dashboard layout."""
        self.pack(fill="both", expand=True)
        self._build_header()
        self._build_toolbar()
        self._build_stats()
        self._build_list()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=Theme.PANEL, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🔒",
            font=("Segoe UI", 22),
            bg=Theme.PANEL,
            fg=Theme.HIGHLIGHT
        ).pack(side="left", padx=(20, 8), pady=12)

        tk.Label(
            header,
            text="Password Vault",
            font=Theme.FONT_HEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left", pady=12)

        tk.Button(
            header,
            text="＋  Add Password",
            font=Theme.FONT_BUTTON,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._handle_add
        ).pack(side="right", padx=16, pady=12)

    def _build_toolbar(self) -> None:
        toolbar = tk.Frame(self, bg=Theme.TOOLBAR if hasattr(Theme, 'TOOLBAR') else Theme.PANEL, height=44)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        tk.Label(
            toolbar,
            text="🔍",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(side="left", padx=(16, 4))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._on_search())

        tk.Entry(
            toolbar,
            textvariable=self._search_var,
            font=Theme.FONT_BODY,
            bg=Theme.ENTRY_BG,
            fg=Theme.TEXT,
            insertbackground=Theme.TEXT,
            relief="flat",
            bd=6,
            width=40
        ).pack(side="left", ipady=3, pady=6)

    def _build_stats(self) -> None:
        self._stats_frame = tk.Frame(self, bg=Theme.BACKGROUND, height=70)
        self._stats_frame.pack(fill="x", padx=16, pady=8)
        self._render_stats()

    def _render_stats(self) -> None:
        for widget in self._stats_frame.winfo_children():
            widget.destroy()

        stats = get_password_statistics()

        cards = [
            ("Total",     str(stats["total_passwords"]),    Theme.TEXT),
            ("Favorites", str(stats["favorite_passwords"]), Theme.HIGHLIGHT),
            ("Weak",      str(stats["weak_passwords"]),     Theme.WARNING),
            ("Categories",str(stats["categories"]),         Theme.SUBTLE),
        ]

        for label, value, colour in cards:
            card = tk.Frame(self._stats_frame, bg=Theme.PANEL, padx=16, pady=8)
            card.pack(side="left", expand=True, fill="x", padx=4)

            tk.Label(
                card,
                text=value,
                font=("Segoe UI", 16, "bold"),
                bg=Theme.PANEL,
                fg=colour
            ).pack()

            tk.Label(
                card,
                text=label,
                font=Theme.FONT_SMALL,
                bg=Theme.PANEL,
                fg=Theme.SUBTLE
            ).pack()

    def _build_list(self) -> None:
        list_container = tk.Frame(self, bg=Theme.BACKGROUND)
        list_container.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        canvas = tk.Canvas(list_container, bg=Theme.BACKGROUND, highlightthickness=0)
        sb = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        self._list_inner = tk.Frame(canvas, bg=Theme.BACKGROUND)
        win = canvas.create_window((0, 0), window=self._list_inner, anchor="nw")
        self._list_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

    def _load_data(self) -> None:
        self._passwords = load_all_passwords()
        self._render_list()
        self._render_stats()

    def _on_search(self) -> None:
        self._search_query = self._search_var.get().lower().strip()
        self._render_list()

    def _get_filtered(self) -> list[PasswordEntry]:
        if not self._search_query:
            return self._passwords
        q = self._search_query
        return [
            p for p in self._passwords
            if q in p.title.lower()
            or q in p.username.lower()
            or q in (p.url or "").lower()
            or q in (p.notes or "").lower()
        ]

    def _render_list(self) -> None:
        for widget in self._list_inner.winfo_children():
            widget.destroy()

        entries = self._get_filtered()

        if not entries:
            self._render_empty()
            return

        for entry in entries:
            self._render_entry_row(entry)

    def _render_empty(self) -> None:
        tk.Label(
            self._list_inner,
            text="🔑",
            font=("Segoe UI", 40),
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(pady=(60, 8))

        msg = "No passwords match your search." if self._search_query else "No passwords yet."
        sub = "Try a different query." if self._search_query else "Click ＋ Add Password to create your first entry."

        tk.Label(
            self._list_inner,
            text=msg,
            font=Theme.FONT_SUBHEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack()

        tk.Label(
            self._list_inner,
            text=sub,
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(pady=(4, 0))

    def _render_entry_row(self, entry: PasswordEntry) -> None:
        row = tk.Frame(self._list_inner, bg=Theme.PANEL, padx=16, pady=12)
        row.pack(fill="x", padx=4, pady=3)

        # Left: title + username
        left = tk.Frame(row, bg=Theme.PANEL)
        left.pack(side="left", fill="x", expand=True)

        title_row = tk.Frame(left, bg=Theme.PANEL)
        title_row.pack(fill="x", anchor="w")

        star = "⭐  " if entry.is_favorite else ""
        tk.Label(
            title_row,
            text=f"{star}{entry.title}",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left")

        colour = STRENGTH_COLOURS.get(entry.strength_label(), Theme.SUBTLE)
        tk.Label(
            title_row,
            text=f"  ● {entry.strength_label()}",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=colour
        ).pack(side="left")

        tk.Label(
            left,
            text=f"👤  {entry.username}",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(2, 0))

        if entry.url:
            tk.Label(
                left,
                text=f"🌐  {entry.display_url()}",
                font=Theme.FONT_SMALL,
                bg=Theme.PANEL,
                fg=Theme.SUBTLE
            ).pack(anchor="w")

        # Right: action buttons
        actions = tk.Frame(row, bg=Theme.PANEL)
        actions.pack(side="right")

        for text, cmd in [
            ("📋 User", lambda e=entry: self._copy_username(e)),
            ("🔑 Pass", lambda e=entry: self._copy_password(e)),
            ("✏  Edit", lambda e=entry: self._handle_edit(e)),
            ("🗑",      lambda e=entry: self._handle_delete(e)),
        ]:
            tk.Button(
                actions,
                text=text,
                font=Theme.FONT_SMALL,
                bg=Theme.ACCENT,
                fg=Theme.TEXT,
                relief="flat",
                padx=8,
                pady=4,
                cursor="hand2",
                command=cmd
            ).pack(side="left", padx=2)

    # ── Actions ────────────────────────────────────────────────────────────────

    def _handle_add(self) -> None:
        PasswordEditor(
            parent          = self,
            master_password = self._master_password,
            entry           = None,
            on_saved        = self._on_saved
        )

    def _handle_edit(self, entry: PasswordEntry) -> None:
        PasswordEditor(
            parent          = self,
            master_password = self._master_password,
            entry           = entry,
            on_saved        = self._on_saved
        )

    def _handle_delete(self, entry: PasswordEntry) -> None:
        if self._dialogs.confirm_destructive(
            "Delete Password",
            f"Delete '{entry.title}'?"
        ):
            delete_password(entry.id)
            self._notifications.success(f"Deleted: {entry.title}")
            self._notification_center.add(
                "Password Deleted", f"{entry.title} removed.",
                "info", "password_vault"
            )
            self._activity_service.record(
                "PasswordDeleted", "password_vault", entry.title
            )
            self._load_data()

    def _copy_username(self, entry: PasswordEntry) -> None:
        self._clipboard.copy_text(
            entry.username,
            module_id="password_vault",
            auto_clear_seconds=30
        )
        self._notifications.success(f"Username copied. Clears in 30s.")
        self._activity_service.record(
            "UsernameCopied", "password_vault", entry.title
        )

    def _copy_password(self, entry: PasswordEntry) -> None:
        decrypted = decrypt_file_to_memory_string(
            entry.password_encrypted, self._master_password
        )
        if not decrypted:
            self._notifications.error("Failed to decrypt password.")
            return

        self._clipboard.copy_text(
            decrypted,
            module_id="password_vault",
            auto_clear_seconds=30
        )
        update_last_accessed(entry.id)
        self._recent_items.record_access(
            item_id=str(entry.id),
            module_id="password_vault",
            name=entry.title,
            item_type="password"
        )
        self._notifications.success(f"Password copied. Clears in 30s.")
        self._notification_center.add(
            "Password Copied",
            f"{entry.title} - auto-clears in 30 seconds.",
            "info", "password_vault"
        )
        self._activity_service.record(
            "PasswordCopied", "password_vault", entry.title
        )

    def _on_saved(self) -> None:
        self._notifications.success("Password saved.")
        self._activity_service.record(
            "PasswordSaved", "password_vault"
        )
        self._load_data()
