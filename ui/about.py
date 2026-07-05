"""
ui/about.py

About screen for the Secure Vault Platform.
"""

import tkinter as tk
from typing import Callable

from vaultcore.config import PLATFORM_NAME, PLATFORM_VERSION
from vaultcore.theme import Theme


class AboutScreen(tk.Frame):
    """
    Displays platform version, build information,
    and acknowledgements.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_close: Callable
    ) -> None:
        """
        Initialize the about screen.

        Args:
            parent:   The parent widget.
            on_close: Callback to return to the home screen.
        """
        super().__init__(parent, bg=Theme.BACKGROUND)
        self._on_close = on_close
        self._build()

    def _build(self) -> None:
        """Construct the about screen."""
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
            text=f"ℹ  About {PLATFORM_NAME}",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left", padx=8)

        # Content
        content = tk.Frame(self, bg=Theme.BACKGROUND)
        content.pack(fill="both", expand=True)

        panel = tk.Frame(content, bg=Theme.PANEL, padx=48, pady=48)
        panel.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            panel,
            text="🔐",
            font=("Segoe UI", 48),
            bg=Theme.PANEL,
            fg=Theme.HIGHLIGHT
        ).pack(pady=(0, 16))

        tk.Label(
            panel,
            text=PLATFORM_NAME,
            font=Theme.FONT_TITLE,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack()

        tk.Label(
            panel,
            text=f"Version {PLATFORM_VERSION}",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(pady=(4, 24))

        tk.Frame(panel, bg=Theme.ACCENT, height=1).pack(fill="x", pady=(0, 24))

        details = [
            ("Platform",     PLATFORM_NAME),
            ("Version",      PLATFORM_VERSION),
            ("Module 1",     "Personal Document Vault v1.0.0"),
            ("Architecture", "VaultCore + Module System"),
            ("Encryption",   "AES-256-GCM"),
            ("Storage",      "Fully Offline — Local Only"),
            ("Network",      "Zero — No Internet Connection"),
        ]

        for label, value in details:
            row = tk.Frame(panel, bg=Theme.PANEL)
            row.pack(fill="x", pady=4)

            tk.Label(
                row,
                text=label,
                font=Theme.FONT_LABEL,
                bg=Theme.PANEL,
                fg=Theme.SUBTLE,
                width=14,
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

        tk.Frame(panel, bg=Theme.ACCENT, height=1).pack(fill="x", pady=(24, 16))

        tk.Label(
            panel,
            text="Privacy-first secure desktop software.",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack()
