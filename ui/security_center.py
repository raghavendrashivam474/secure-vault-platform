"""
ui/security_center.py

Security Center for the Secure Vault Platform.

Provides a real-time overview of platform security status,
session information, and vault health indicators.
"""

import tkinter as tk
from typing import Callable
from pathlib import Path
from datetime import datetime

from vaultcore.session import SessionManager
from vaultcore.settings_service import SettingsService, AUTO_LOCK_OPTIONS
from vaultcore.theme import Theme
from vaultcore.database import get_vault_statistics
from vaultcore.backup import get_latest_backup_date, get_backup_count
from vaultcore.config import PLATFORM_VERSION


class SecurityCenter(tk.Frame):
    """
    Displays platform security status, session details,
    vault statistics, and backup information.
    """

    def __init__(
        self,
        parent: tk.Widget,
        session_manager: SessionManager,
        settings_service: SettingsService,
        on_close: Callable
    ) -> None:
        """
        Initialize the security center.

        Args:
            parent:           The parent widget.
            session_manager:  The platform session manager.
            settings_service: The platform settings service.
            on_close:         Callback to return to the dashboard.
        """
        super().__init__(parent, bg=Theme.BACKGROUND)
        self._session_manager  = session_manager
        self._settings_service = settings_service
        self._on_close         = on_close
        self._build()

    def _build(self) -> None:
        """Construct the security center layout."""
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
            text="🛡  Security Center",
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
            command=self._refresh
        ).pack(side="right", padx=16, pady=10)

        # Scrollable body
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

        self._render_content()

    def _refresh(self) -> None:
        """Refresh all security center data."""
        for widget in self._body.winfo_children():
            widget.destroy()
        self._render_content()

    def _render_content(self) -> None:
        """Render all security center sections."""
        left  = tk.Frame(self._body, bg=Theme.BACKGROUND)
        right = tk.Frame(self._body, bg=Theme.BACKGROUND)
        left.pack(side="left", fill="both", expand=True, padx=(32, 16), pady=32)
        right.pack(side="left", fill="both", expand=True, padx=(16, 32), pady=32)

        self._render_session_section(left)
        self._render_platform_section(left)
        self._render_vault_section(right)
        self._render_backup_section(right)

    def _render_session_section(self, parent: tk.Widget) -> None:
        """Render the current session information."""
        panel = self._section(parent, "🔑  Current Session")

        session = self._session_manager.get_session()

        if session and session.is_authenticated:
            status_text  = "✓  Platform Unlocked"
            status_color = Theme.SUCCESS
            login_time   = session.formatted_login_time()
            idle_secs    = int(session.idle_seconds())
        else:
            status_text  = "🔒  Platform Locked"
            status_color = Theme.ERROR
            login_time   = "—"
            idle_secs    = 0

        tk.Label(
            panel,
            text=status_text,
            font=("Segoe UI", 13, "bold"),
            bg=Theme.PANEL,
            fg=status_color
        ).pack(anchor="w", pady=(0, 12))

        auto_lock = self._settings_service.get("auto_lock")

        rows = [
            ("Login Time",  login_time),
            ("Idle Time",   f"{idle_secs}s"),
            ("Auto-Lock",   auto_lock),
        ]
        for label, value in rows:
            self._info_row(panel, label, value)

    def _render_platform_section(self, parent: tk.Widget) -> None:
        """Render platform information."""
        panel = self._section(parent, "🖥  Platform")

        rows = [
            ("Version",     PLATFORM_VERSION),
            ("Encryption",  "AES-256-GCM"),
            ("Network",     "Offline Only"),
            ("Storage",     "Local"),
        ]
        for label, value in rows:
            self._info_row(panel, label, value)

    def _render_vault_section(self, parent: tk.Widget) -> None:
        """Render vault statistics."""
        panel = self._section(parent, "📊  Vault Statistics")

        try:
            stats = get_vault_statistics()
            rows  = [
                ("Documents",        str(stats["document_count"])),
                ("Categories",       str(stats["category_count"])),
                ("Favorites",        str(stats["favorite_count"])),
                ("Integrity Issues", str(stats["integrity_issues"])),
                ("Expired Docs",     str(stats["expired_count"])),
                ("Vault Created",    stats["created_at"]),
            ]
        except Exception:
            rows = [("Status", "No vault data available")]

        for label, value in rows:
            self._info_row(panel, label, value)

    def _render_backup_section(self, parent: tk.Widget) -> None:
        """Render backup status."""
        panel = self._section(parent, "💾  Backup Status")

        latest    = get_latest_backup_date() or "Never"
        count     = get_backup_count()
        frequency = self._settings_service.get("backup_frequency")

        rows = [
            ("Latest Backup",  latest),
            ("Total Backups",  str(count)),
            ("Auto-Backup",    frequency),
        ]
        for label, value in rows:
            self._info_row(panel, label, value)

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

    def _info_row(
        self,
        parent: tk.Widget,
        label: str,
        value: str
    ) -> None:
        """Render a key-value info row."""
        row = tk.Frame(parent, bg=Theme.PANEL)
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
            fg=Theme.TEXT,
            anchor="w"
        ).pack(side="left")
