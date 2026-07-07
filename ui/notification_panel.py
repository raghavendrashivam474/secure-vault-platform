"""
ui/notification_panel.py

Notification Center UI for the Secure Vault Platform.

Displays notification history with read/unread tracking
and dismissal controls.
"""

import tkinter as tk
from typing import Callable

from vaultcore.notification_center import NotificationCenter, Notification
from vaultcore.theme import Theme


SEVERITY_COLOURS = {
    "info":    Theme.ACCENT,
    "success": Theme.SUCCESS,
    "warning": Theme.WARNING,
    "error":   Theme.ERROR,
}

SEVERITY_ICONS = {
    "info":    "ℹ",
    "success": "✓",
    "warning": "⚠",
    "error":   "✗",
}


class NotificationPanel(tk.Frame):
    """
    Notification Center panel displaying persistent notifications.
    """

    def __init__(
        self,
        parent: tk.Widget,
        notification_center: NotificationCenter,
        on_close: Callable
    ) -> None:
        """
        Initialize the notification panel.

        Args:
            parent:              The parent widget.
            notification_center: The notification center service.
            on_close:            Callback to return to dashboard.
        """
        super().__init__(parent, bg=Theme.BACKGROUND)
        self._center   = notification_center
        self._on_close = on_close
        self._build()

    def _build(self) -> None:
        """Construct the notification panel."""
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
            text="🔔  Notification Center",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left", padx=8)

        tk.Button(
            header,
            text="Mark All Read",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            activebackground=Theme.HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._mark_all_read
        ).pack(side="right", padx=(0, 6), pady=10)

        tk.Button(
            header,
            text="Clear All",
            font=Theme.FONT_BODY,
            bg="#8b0000",
            fg="#ffffff",
            activebackground=Theme.HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._clear_all
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
        """Render all notifications."""
        for widget in self._body.winfo_children():
            widget.destroy()

        notifications = self._center.get_all(limit=100)

        if not notifications:
            tk.Label(
                self._body,
                text="🔕",
                font=("Segoe UI", 36),
                bg=Theme.BACKGROUND,
                fg=Theme.SUBTLE
            ).pack(pady=(60, 8))

            tk.Label(
                self._body,
                text="No notifications yet.",
                font=Theme.FONT_SUBHEADING,
                bg=Theme.BACKGROUND,
                fg=Theme.TEXT
            ).pack()
            return

        for notif in notifications:
            self._render_notification(notif)

    def _render_notification(self, notif: Notification) -> None:
        """Render a single notification card."""
        colour = SEVERITY_COLOURS.get(notif.severity, Theme.ACCENT)
        icon   = SEVERITY_ICONS.get(notif.severity, "•")

        bg = Theme.PANEL if notif.is_read else Theme.ACCENT

        card = tk.Frame(self._body, bg=bg, padx=16, pady=12)
        card.pack(fill="x", padx=40, pady=6)

        header_row = tk.Frame(card, bg=bg)
        header_row.pack(fill="x")

        tk.Label(
            header_row,
            text=f"{icon}  {notif.title}",
            font=Theme.FONT_SUBHEADING,
            bg=bg,
            fg=colour
        ).pack(side="left")

        tk.Label(
            header_row,
            text=notif.created_at[:19].replace("T", " "),
            font=Theme.FONT_SMALL,
            bg=bg,
            fg=Theme.SUBTLE
        ).pack(side="right")

        tk.Label(
            card,
            text=notif.message,
            font=Theme.FONT_BODY,
            bg=bg,
            fg=Theme.TEXT,
            wraplength=800,
            justify="left",
            anchor="w"
        ).pack(fill="x", pady=(4, 4))

        actions = tk.Frame(card, bg=bg)
        actions.pack(fill="x", pady=(4, 0))

        tk.Label(
            actions,
            text=f"from {notif.module_id}",
            font=Theme.FONT_SMALL,
            bg=bg,
            fg=Theme.SUBTLE
        ).pack(side="left")

        tk.Button(
            actions,
            text="Dismiss",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE,
            activebackground=Theme.HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            command=lambda n=notif: self._dismiss(n)
        ).pack(side="right")

    def _dismiss(self, notif: Notification) -> None:
        """Dismiss a notification."""
        if notif.id:
            self._center.dismiss(notif.id)
        self._render()

    def _mark_all_read(self) -> None:
        """Mark all notifications as read."""
        self._center.mark_all_read()
        self._render()

    def _clear_all(self) -> None:
        """Clear all notifications."""
        self._center.clear_all()
        self._render()
