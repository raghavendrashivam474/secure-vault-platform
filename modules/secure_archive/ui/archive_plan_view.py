"""
modules/secure_archive/ui/archive_plan_view.py

Archive plan preview dialog.

Shows the user what will be archived before confirmation.
"""

import tkinter as tk
from typing import Callable

from vaultcore.theme import Theme

from modules.secure_archive.models.archive_plan import ArchivePlan
from modules.secure_archive.models.compression import STRATEGY_LABELS
from modules.secure_archive.models.classification import CLASS_LABELS


class ArchivePlanView(tk.Toplevel):
    """
    Preview dialog showing what an archive will contain.

    Users see:
      - Project type and confidence
      - Files to include vs ignore
      - Size summaries
      - Strategy breakdown
    """

    def __init__(
        self,
        parent: tk.Widget,
        plan: ArchivePlan,
        on_confirm: Callable
    ) -> None:
        super().__init__(parent)
        self.title("Archive Plan Preview")
        self.geometry("720x640")
        self.configure(bg=Theme.BACKGROUND)
        self.grab_set()

        self._plan       = plan
        self._on_confirm = on_confirm
        self._build()

    def _build(self) -> None:
        # Header
        tk.Label(
            self,
            text="📦  Archive Plan",
            font=Theme.FONT_HEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(pady=(20, 8))

        tk.Label(
            self,
            text=f"Review before creating the archive.",
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(pady=(0, 16))

        # Project details panel
        project_frame = tk.Frame(self, bg=Theme.PANEL, padx=20, pady=16)
        project_frame.pack(fill="x", padx=24, pady=(0, 12))

        tk.Label(
            project_frame,
            text=f"{self._plan.project_profile.icon}  {self._plan.project_profile.label}",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(anchor="w")

        tk.Label(
            project_frame,
            text=f"Confidence: {self._plan.project_profile.confidence}",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(2, 8))

        # Stats grid
        stats_frame = tk.Frame(self, bg=Theme.BACKGROUND)
        stats_frame.pack(fill="x", padx=24, pady=(0, 12))

        stats = [
            ("Files to Include",  f"{self._plan.file_count:,}",        Theme.SUCCESS),
            ("Files to Ignore",   f"{self._plan.ignored_count:,}",     Theme.WARNING),
            ("Archive Input",     self._plan.formatted_size(self._plan.included_size), Theme.SUCCESS),
            ("Ignored",           self._plan.formatted_size(self._plan.ignored_size),  Theme.WARNING),
        ]

        for label, value, colour in stats:
            card = tk.Frame(stats_frame, bg=Theme.PANEL, padx=12, pady=10)
            card.pack(side="left", expand=True, fill="x", padx=3)

            tk.Label(
                card,
                text=value,
                font=("Segoe UI", 14, "bold"),
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

        # Scrollable body for strategy + ignore breakdown
        canvas = tk.Canvas(self, bg=Theme.BACKGROUND, highlightthickness=0)
        sb     = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        body = tk.Frame(canvas, bg=Theme.BACKGROUND)
        win = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width)
        )

        # Strategy breakdown
        if self._plan.strategy_summary:
            tk.Label(
                body,
                text="Compression Strategy",
                font=Theme.FONT_LABEL,
                bg=Theme.BACKGROUND,
                fg=Theme.SUBTLE
            ).pack(anchor="w", pady=(0, 6))

            for strat, count in sorted(self._plan.strategy_summary.items(), key=lambda x: -x[1]):
                label = STRATEGY_LABELS.get(strat, strat)
                self._render_row(body, label, f"{count} files")

        # Ignore breakdown
        if self._plan.ignore_summary:
            tk.Label(
                body,
                text="Top Ignore Rules",
                font=Theme.FONT_LABEL,
                bg=Theme.BACKGROUND,
                fg=Theme.SUBTLE
            ).pack(anchor="w", pady=(16, 6))

            sorted_ignore = sorted(self._plan.ignore_summary.items(), key=lambda x: -x[1])
            for rule, count in sorted_ignore[:10]:
                self._render_row(body, rule, f"{count} files")

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
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.destroy
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            button_frame,
            text=f"✓  Create Archive ({self._plan.file_count} files)",
            font=Theme.FONT_BUTTON,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._handle_confirm
        ).pack(side="right")

    def _render_row(self, parent, label: str, value: str) -> None:
        row = tk.Frame(parent, bg=Theme.PANEL, padx=12, pady=6)
        row.pack(fill="x", pady=2)

        tk.Label(
            row,
            text=label,
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.TEXT,
            anchor="w"
        ).pack(side="left", fill="x", expand=True)

        tk.Label(
            row,
            text=value,
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(side="right")

    def _handle_confirm(self) -> None:
        self._on_confirm()
        self.destroy()
