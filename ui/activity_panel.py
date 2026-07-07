"""
ui/activity_panel.py

Activity Feed UI for the Secure Vault Platform.

Displays recent platform activity for user review.
"""

import tkinter as tk
from typing import Callable

from vaultcore.recent_activity import RecentActivityService, ActivityEntry
from vaultcore.theme import Theme


class ActivityPanel(tk.Frame):
    """
    Activity feed panel showing recent platform events.
    """

    def __init__(
        self,
        parent: tk.Widget,
        activity_service: RecentActivityService,
        on_close: Callable
    ) -> None:
        """
        Initialize the activity panel.

        Args:
            parent:           The parent widget.
            activity_service: The recent activity service.
            on_close:         Callback to return to dashboard.
        """
        super().__init__(parent, bg=Theme.BACKGROUND)
        self._service  = activity_service
        self._on_close = on_close
        self._build()

    def _build(self) -> None:
        """Construct the activity panel."""
        self.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self, bg=Theme.PANEL, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Button(
            header,
            text="←  Back",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            activebackground=Theme.HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_close
        ).pack(side="left", padx=16, pady=10)

        tk.Label(
            header,
            text="🕒  Recent Activity",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left", padx=8)

        tk.Button(
            header,
            text="🔄  Refresh",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            activebackground=Theme.HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._render
        ).pack(side="right", padx=16, pady=10)

        # Scrollable list
        canvas = tk.Canvas(self, bg=Theme.BACKGROUND, highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

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

        self._render()

    def _render(self) -> None:
        """Render all activity entries."""
        for widget in self._body.winfo_children():
            widget.destroy()

        entries = self._service.get_recent(limit=100)

        if not entries:
            tk.Label(
                self._body,
                text="📭",
                font=("Segoe UI", 36),
                bg=Theme.BACKGROUND,
                fg=Theme.SUBTLE
            ).pack(pady=(60, 8))

            tk.Label(
                self._body,
                text="No recent activity.",
                font=Theme.FONT_SUBHEADING,
                bg=Theme.BACKGROUND,
                fg=Theme.TEXT
            ).pack()
            return

        for entry in entries:
            self._render_entry(entry)

    def _render_entry(self, entry: ActivityEntry) -> None:
        """Render a single activity entry."""
        row = tk.Frame(self._body, bg=Theme.PANEL, padx=16, pady=10)
        row.pack(fill="x", padx=40, pady=3)

        left = tk.Frame(row, bg=Theme.PANEL)
        left.pack(side="left", fill="x", expand=True)

        tk.Label(
            left,
            text=f"● {entry.activity}",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(anchor="w")

        if entry.detail:
            tk.Label(
                left,
                text=entry.detail,
                font=Theme.FONT_SMALL,
                bg=Theme.PANEL,
                fg=Theme.SUBTLE
            ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            left,
            text=f"{entry.module_id}",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w")

        tk.Label(
            row,
            text=entry.created_at[:19].replace("T", " "),
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(side="right")
