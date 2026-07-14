"""
modules/secure_archive/ui/dashboard.py

Secure Archive dashboard - Sprint 14 placeholder.
Full functionality will be built incrementally.
"""

import tkinter as tk
from typing import Callable

from vaultcore.theme import Theme


class SecureArchiveDashboard(tk.Frame):
    """Sprint 14.1 - Module placeholder. Full UI arrives in later milestones."""

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
        storage_manager,
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
        self._storage_manager     = storage_manager
        self._on_close            = on_close

        self._build()

    def _build(self) -> None:
        """Construct placeholder dashboard."""
        self.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self, bg=Theme.PANEL, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="📦",
            font=("Segoe UI", 22),
            bg=Theme.PANEL,
            fg=Theme.HIGHLIGHT
        ).pack(side="left", padx=(20, 8), pady=12)

        tk.Label(
            header,
            text="Secure Archive",
            font=Theme.FONT_HEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left", pady=12)

        # Body placeholder
        body = tk.Frame(self, bg=Theme.BACKGROUND)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="📦",
            font=("Segoe UI", 80),
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(pady=(80, 20))

        tk.Label(
            body,
            text="Secure Archive",
            font=("Segoe UI", 20, "bold"),
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack()

        tk.Label(
            body,
            text="v0.1.0 - Sprint 14 Foundation",
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(pady=(4, 20))

        tk.Label(
            body,
            text="Intelligent project archiving and verified restoration.\n"
                 "Archive engine implementation in progress.\n\n"
                 "Full functionality will be delivered across Sprint 14 milestones.",
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE,
            justify="center"
        ).pack()
