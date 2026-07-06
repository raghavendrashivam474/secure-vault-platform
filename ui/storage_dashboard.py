"""
ui/storage_dashboard.py

Storage Health Dashboard for the Secure Vault Platform.

Displays platform-wide storage statistics, health status,
module storage breakdown, and backup information.
"""

import tkinter as tk
from typing import Callable

from vaultcore.storage_health import StorageHealthService
from vaultcore.theme import Theme


HEALTH_COLOURS = {
    "healthy":  Theme.SUCCESS,
    "warning":  Theme.WARNING,
    "critical": Theme.ERROR,
}


class StorageDashboard(tk.Frame):
    """
    Storage health and analytics dashboard.

    Provides real-time visibility into platform storage
    utilization across all modules and services.
    """

    def __init__(
        self,
        parent: tk.Widget,
        health_service: StorageHealthService,
        on_close: Callable
    ) -> None:
        """
        Initialize the Storage Dashboard.

        Args:
            parent:         The parent widget.
            health_service: The platform storage health service.
            on_close:       Callback to return to previous screen.
        """
        super().__init__(parent, bg=Theme.BACKGROUND)
        self._health_service = health_service
        self._on_close       = on_close
        self._build()

    def _build(self) -> None:
        """Construct the storage dashboard layout."""
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
            text="💾  Storage Health",
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
        sb     = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
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
        """Refresh storage statistics."""
        for widget in self._body.winfo_children():
            widget.destroy()
        self._render_content()

    def _render_content(self) -> None:
        """Render all storage sections."""
        report = self._health_service.get_full_report()

        pad = {"padx": 40}

        # Overall status
        health        = report.get("health_status", "unknown")
        health_colour = HEALTH_COLOURS.get(health, Theme.SUBTLE)

        tk.Label(
            self._body,
            text=f"{'✓' if health == 'healthy' else '⚠'}  Storage {health.capitalize()}",
            font=("Segoe UI", 18, "bold"),
            bg=Theme.BACKGROUND,
            fg=health_colour
        ).pack(pady=(36, 4), **pad)

        # Summary cards
        summary_frame = tk.Frame(self._body, bg=Theme.BACKGROUND)
        summary_frame.pack(fill="x", **pad, pady=(16, 24))

        cards = [
            ("Vault Size",    report.get("vault_size_fmt",   "0 B")),
            ("Indexed Files", str(report.get("total_files",  0))),
            ("Backup Size",   report.get("backup_size_fmt",  "0 B")),
            ("Backups",       str(report.get("backup_count", 0))),
            ("Cache",         report.get("cache_size_fmt",   "0 B")),
            ("Temp",          report.get("temp_size_fmt",    "0 B")),
        ]

        for col, (label, value) in enumerate(cards):
            self._summary_card(summary_frame, label, value, col)

        summary_frame.columnconfigure(tuple(range(len(cards))), weight=1)

        tk.Frame(
            self._body, bg=Theme.ACCENT, height=1
        ).pack(fill="x", **pad, pady=(0, 20))

        # Two column detail layout
        left  = tk.Frame(self._body, bg=Theme.BACKGROUND)
        right = tk.Frame(self._body, bg=Theme.BACKGROUND)
        left.pack(side="left", fill="both", expand=True, padx=(40, 16), pady=(0, 32))
        right.pack(side="left", fill="both", expand=True, padx=(16, 40), pady=(0, 32))

        self._render_storage_breakdown(left, report)
        self._render_backup_section(right, report)

    def _summary_card(
        self,
        parent: tk.Widget,
        label: str,
        value: str,
        column: int
    ) -> None:
        """Render a summary statistics card."""
        card = tk.Frame(parent, bg=Theme.PANEL, padx=16, pady=14)
        card.grid(row=0, column=column, padx=6, sticky="nsew")

        tk.Label(
            card,
            text=value,
            font=("Segoe UI", 18, "bold"),
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack()

        tk.Label(
            card,
            text=label,
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack()

    def _render_storage_breakdown(
        self,
        parent: tk.Widget,
        report: dict
    ) -> None:
        """Render the storage breakdown section."""
        panel = self._section(parent, "📊  Storage Breakdown")

        rows = [
            ("Documents",  report.get("doc_vault_size",  "0 B")),
            ("Backups",    report.get("backup_size_fmt", "0 B")),
            ("Cache",      report.get("cache_size_fmt",  "0 B")),
            ("Temp Files", report.get("temp_size_fmt",   "0 B")),
            ("Logs",       report.get("log_size_fmt",    "0 B")),
            ("Indexed",    report.get("indexed_size_fmt","0 B")),
        ]

        for label, value in rows:
            self._info_row(panel, label, value)

    def _render_backup_section(
        self,
        parent: tk.Widget,
        report: dict
    ) -> None:
        """Render the backup status section."""
        panel = self._section(parent, "💾  Backup Status")

        rows = [
            ("Latest Backup",  report.get("latest_backup",  "Never")),
            ("Total Backups",  str(report.get("backup_count", 0))),
            ("Backup Size",    report.get("backup_size_fmt", "0 B")),
        ]

        for label, value in rows:
            self._info_row(panel, label, value)

    def _section(self, parent: tk.Widget, title: str) -> tk.Frame:
        """Create a titled section panel."""
        outer = tk.Frame(parent, bg=Theme.BACKGROUND)
        outer.pack(fill="x", pady=(0, 16))

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
