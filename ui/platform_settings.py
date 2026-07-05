"""
ui/platform_settings.py

Platform Settings Screen for the Secure Vault Platform.

Provides centralized settings management for all
platform-wide preferences. Module-specific settings
remain inside their respective modules.
"""

import tkinter as tk
from typing import Callable

from vaultcore.settings_service import SettingsService, AUTO_LOCK_OPTIONS
from vaultcore.theme import Theme
from vaultcore.activity_monitor import ActivityMonitor
from vaultcore.logger import log_event


class PlatformSettingsScreen(tk.Frame):
    """
    Platform-wide settings screen.

    Covers auto-lock, backup preferences,
    notifications, and theme selection.
    """

    def __init__(
        self,
        parent: tk.Widget,
        settings_service: SettingsService,
        activity_monitor: ActivityMonitor,
        on_close: Callable
    ) -> None:
        """
        Initialize the platform settings screen.

        Args:
            parent:           The parent widget.
            settings_service: The shared settings service.
            activity_monitor: The platform activity monitor.
            on_close:         Callback to return to dashboard.
        """
        super().__init__(parent, bg=Theme.BACKGROUND)
        self._settings    = settings_service
        self._monitor     = activity_monitor
        self._on_close    = on_close
        self._build()

    def _build(self) -> None:
        """Construct the settings screen layout."""
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
            text="⚙  Platform Settings",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left", padx=8)

        # Scrollable body
        canvas = tk.Canvas(self, bg=Theme.BACKGROUND, highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        body = tk.Frame(canvas, bg=Theme.BACKGROUND)
        win  = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width)
        )

        left  = tk.Frame(body, bg=Theme.BACKGROUND)
        right = tk.Frame(body, bg=Theme.BACKGROUND)
        left.pack(side="left", fill="both", expand=True, padx=(32, 16), pady=32)
        right.pack(side="left", fill="both", expand=True, padx=(16, 32), pady=32)

        self._build_autolock_section(left)
        self._build_backup_section(left)
        self._build_notifications_section(right)
        self._build_about_section(right)

    def _build_autolock_section(self, parent: tk.Widget) -> None:
        """Build the auto-lock settings section."""
        panel = self._section(parent, "⏱  Auto-Lock")

        tk.Label(
            panel,
            text="Lock platform after inactivity:",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(0, 10))

        saved = self._settings.get("auto_lock")
        self._auto_lock_var = tk.StringVar(value=saved)

        for option in AUTO_LOCK_OPTIONS.keys():
            tk.Radiobutton(
                panel,
                text=option,
                variable=self._auto_lock_var,
                value=option,
                font=Theme.FONT_BODY,
                bg=Theme.PANEL,
                fg=Theme.TEXT,
                activebackground=Theme.PANEL,
                selectcolor=Theme.ACCENT,
                command=self._save_auto_lock
            ).pack(anchor="w", pady=2)

    def _build_backup_section(self, parent: tk.Widget) -> None:
        """Build the backup frequency settings section."""
        panel = self._section(parent, "💾  Auto-Backup")

        tk.Label(
            panel,
            text="Automatic backup frequency:",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(0, 10))

        saved = self._settings.get("backup_frequency")
        self._backup_var = tk.StringVar(value=saved)

        for option in ["Never", "Daily", "Weekly", "Monthly"]:
            tk.Radiobutton(
                panel,
                text=option,
                variable=self._backup_var,
                value=option,
                font=Theme.FONT_BODY,
                bg=Theme.PANEL,
                fg=Theme.TEXT,
                activebackground=Theme.PANEL,
                selectcolor=Theme.ACCENT,
                command=self._save_backup_frequency
            ).pack(anchor="w", pady=2)

    def _build_notifications_section(self, parent: tk.Widget) -> None:
        """Build the notifications settings section."""
        panel = self._section(parent, "🔔  Notifications")

        saved = self._settings.get("notifications") == "true"
        self._notif_var = tk.BooleanVar(value=saved)

        tk.Checkbutton(
            panel,
            text="Enable platform notifications",
            variable=self._notif_var,
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.TEXT,
            activebackground=Theme.PANEL,
            selectcolor=Theme.ACCENT,
            command=self._save_notifications
        ).pack(anchor="w", pady=4)

        tk.Label(
            panel,
            text="Notifications appear for backup events,\n"
                 "module launches, and security alerts.",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE,
            justify="left"
        ).pack(anchor="w", pady=(8, 0))

    def _build_about_section(self, parent: tk.Widget) -> None:
        """Build the platform version info section."""
        from vaultcore.config import PLATFORM_NAME, PLATFORM_VERSION
        panel = self._section(parent, "ℹ  Platform Info")

        rows = [
            ("Platform",  PLATFORM_NAME),
            ("Version",   PLATFORM_VERSION),
            ("Security",  "AES-256-GCM"),
            ("Network",   "Offline Only"),
        ]

        for label, value in rows:
            row = tk.Frame(panel, bg=Theme.PANEL)
            row.pack(fill="x", pady=3)
            tk.Label(
                row,
                text=label,
                font=Theme.FONT_LABEL,
                bg=Theme.PANEL,
                fg=Theme.SUBTLE,
                width=12,
                anchor="w"
            ).pack(side="left")
            tk.Label(
                row,
                text=value,
                font=Theme.FONT_BODY,
                bg=Theme.PANEL,
                fg=Theme.TEXT
            ).pack(side="left")

    def _save_auto_lock(self) -> None:
        """Save and apply the auto-lock setting."""
        selected = self._auto_lock_var.get()
        self._settings.set("auto_lock", selected)
        seconds = self._settings.get_auto_lock_seconds()
        self._monitor.set_idle_timeout(seconds)

    def _save_backup_frequency(self) -> None:
        """Save the backup frequency setting."""
        self._settings.set("backup_frequency", self._backup_var.get())

    def _save_notifications(self) -> None:
        """Save the notifications preference."""
        value = "true" if self._notif_var.get() else "false"
        self._settings.set("notifications", value)

    def _section(self, parent: tk.Widget, title: str) -> tk.Frame:
        """Create a titled section panel."""
        outer = tk.Frame(parent, bg=Theme.BACKGROUND)
        outer.pack(fill="x", pady=(0, 20))

        tk.Label(
            outer,
            text=title,
            font=Theme.FONT_SUBHEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(anchor="w", pady=(0, 8))

        panel = tk.Frame(outer, bg=Theme.PANEL, padx=20, pady=16)
        panel.pack(fill="x")
        return panel
