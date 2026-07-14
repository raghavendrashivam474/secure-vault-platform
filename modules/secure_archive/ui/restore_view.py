"""
modules/secure_archive/ui/restore_view.py

Restore preview and result dialogs.
"""

import tkinter as tk
from typing import Callable

from vaultcore.theme import Theme

from modules.secure_archive.models.manifest import ArchiveManifest
from modules.secure_archive.models.restore_result import RestoreReport


class RestorePreviewDialog(tk.Toplevel):
    """Preview dialog before restoring an archive."""

    def __init__(
        self,
        parent: tk.Widget,
        manifest: ArchiveManifest,
        destination: str,
        on_confirm: Callable
    ) -> None:
        super().__init__(parent)
        self.title("Restore Archive Preview")
        self.geometry("560x480")
        self.configure(bg=Theme.BACKGROUND)
        self.grab_set()

        self._manifest    = manifest
        self._destination = destination
        self._on_confirm  = on_confirm
        self._build()

    def _build(self) -> None:
        tk.Label(
            self,
            text="🔄  Restore Archive",
            font=Theme.FONT_HEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(pady=(20, 8))

        tk.Label(
            self,
            text="Archive package validated successfully.",
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND,
            fg=Theme.SUCCESS
        ).pack(pady=(0, 20))

        # Package details
        details = tk.Frame(self, bg=Theme.PANEL, padx=20, pady=16)
        details.pack(fill="x", padx=24)

        rows = [
            ("Archive Name",     self._manifest.archive_name),
            ("Project Type",     self._manifest.project_type),
            ("Files",            f"{self._manifest.file_count:,}"),
            ("Original Size",    self._format_size(self._manifest.original_size)),
            ("Compressed Size",  self._format_size(self._manifest.compressed_size)),
            ("Created",          self._manifest.created_at[:19].replace("T", " ")),
        ]

        for label, value in rows:
            row = tk.Frame(details, bg=Theme.PANEL)
            row.pack(fill="x", pady=3)

            tk.Label(
                row, text=label,
                font=Theme.FONT_LABEL,
                bg=Theme.PANEL, fg=Theme.SUBTLE,
                width=16, anchor="w"
            ).pack(side="left")

            tk.Label(
                row, text=value,
                font=Theme.FONT_BODY,
                bg=Theme.PANEL, fg=Theme.TEXT,
                anchor="w"
            ).pack(side="left")

        # Destination
        tk.Label(
            self,
            text="Restore Destination:",
            font=Theme.FONT_LABEL,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(anchor="w", padx=24, pady=(16, 4))

        tk.Label(
            self,
            text=self._destination,
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT,
            wraplength=500,
            justify="left"
        ).pack(anchor="w", padx=24)

        tk.Label(
            self,
            text="All files will be verified with SHA-256 checksums.",
            font=Theme.FONT_SMALL,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(anchor="w", padx=24, pady=(12, 20))

        # Buttons
        button_frame = tk.Frame(self, bg=Theme.BACKGROUND)
        button_frame.pack(fill="x", padx=24, pady=(0, 20))

        tk.Button(
            button_frame,
            text="Cancel",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE,
            relief="flat",
            padx=16, pady=8,
            cursor="hand2",
            command=self.destroy
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            button_frame,
            text=f"✓  Restore {self._manifest.file_count} Files",
            font=Theme.FONT_BUTTON,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            relief="flat",
            padx=20, pady=8,
            cursor="hand2",
            command=self._handle_confirm
        ).pack(side="right")

    def _handle_confirm(self) -> None:
        self._on_confirm()
        self.destroy()

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 ** 3:
            return f"{size_bytes / (1024 ** 2):.1f} MB"
        else:
            return f"{size_bytes / (1024 ** 3):.2f} GB"


class RestoreReportDialog(tk.Toplevel):
    """Shows restore results after completion."""

    def __init__(
        self,
        parent: tk.Widget,
        report: RestoreReport
    ) -> None:
        super().__init__(parent)
        self.title("Restore Complete")
        self.geometry("500x400")
        self.configure(bg=Theme.BACKGROUND)
        self.grab_set()

        self._report = report
        self._build()

    def _build(self) -> None:
        icon = "✓" if self._report.success else "⚠"
        color = Theme.SUCCESS if self._report.success else Theme.WARNING
        title = "Restore Successful" if self._report.success else "Restore Completed with Issues"

        tk.Label(
            self,
            text=icon,
            font=("Segoe UI", 40),
            bg=Theme.BACKGROUND,
            fg=color
        ).pack(pady=(30, 8))

        tk.Label(
            self,
            text=title,
            font=Theme.FONT_HEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack()

        # Results
        results = tk.Frame(self, bg=Theme.PANEL, padx=20, pady=16)
        results.pack(fill="x", padx=24, pady=20)

        rows = [
            ("Archive",              self._report.archive_name),
            ("Files Expected",       str(self._report.files_expected)),
            ("Files Restored",       str(self._report.files_restored)),
            ("Files Verified",       str(self._report.files_verified)),
            ("Integrity Failures",   str(self._report.integrity_failures)),
            ("Failed",               str(self._report.files_failed)),
            ("Duration",             f"{self._report.duration:.2f}s"),
        ]

        for label, value in rows:
            row = tk.Frame(results, bg=Theme.PANEL)
            row.pack(fill="x", pady=2)

            tk.Label(
                row, text=label,
                font=Theme.FONT_LABEL,
                bg=Theme.PANEL, fg=Theme.SUBTLE,
                width=20, anchor="w"
            ).pack(side="left")

            tk.Label(
                row, text=value,
                font=Theme.FONT_BODY,
                bg=Theme.PANEL, fg=Theme.TEXT
            ).pack(side="left")

        tk.Button(
            self,
            text="OK",
            font=Theme.FONT_BUTTON,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            relief="flat",
            padx=30, pady=8,
            cursor="hand2",
            command=self.destroy
        ).pack(pady=20)
