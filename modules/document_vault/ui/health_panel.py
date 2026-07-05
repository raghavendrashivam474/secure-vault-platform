"""
ui/health_panel.py

Vault Health Check panel for the Personal Document Vault.
Displays a full health scan report with integrity results,
missing files, orphaned files, and duplicate detection.
"""

import tkinter as tk
from typing import Callable

from modules.document_vault.core.integrity import run_vault_health_check
from vaultcore.database import update_integrity_status
from datetime import datetime, timezone


COLOUR_BACKGROUND = "#1a1a2e"
COLOUR_PANEL      = "#16213e"
COLOUR_ACCENT     = "#0f3460"
COLOUR_HIGHLIGHT  = "#e94560"
COLOUR_TEXT       = "#eaeaea"
COLOUR_SUBTLE     = "#a0a0b0"
COLOUR_SUCCESS    = "#51cf66"
COLOUR_WARNING    = "#ffd43b"
COLOUR_ERROR      = "#ff6b6b"


class HealthPanel(tk.Frame):
    """
    Displays vault health check results.
    Runs a full scan and presents findings clearly.
    """

    def __init__(
        self,
        parent: tk.Widget,
        master_password: str,
        on_close: Callable
    ) -> None:
        """
        Initialize the health panel.

        Args:
            parent:          The parent widget.
            master_password: The session master password for decryption.
            on_close:        Callback to close the panel.
        """
        super().__init__(parent, bg=COLOUR_BACKGROUND)
        self._master_password = master_password
        self._on_close        = on_close
        self._build()

    def _build(self) -> None:
        """Construct the health panel layout."""
        self.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self, bg=COLOUR_PANEL, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Button(
            header,
            text="←  Back",
            font=("Segoe UI", 10),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_close
        ).pack(side="left", padx=16, pady=10)

        tk.Label(
            header,
            text="🏥  Vault Health Check",
            font=("Segoe UI", 13, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT
        ).pack(side="left", padx=8)

        tk.Button(
            header,
            text="🔄  Run Scan",
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_HIGHLIGHT,
            fg="#ffffff",
            activebackground=COLOUR_ACCENT,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._run_scan
        ).pack(side="right", padx=16, pady=10)

        # Scrollable results area
        canvas = tk.Canvas(self, bg=COLOUR_BACKGROUND, highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        self._body = tk.Frame(canvas, bg=COLOUR_BACKGROUND)
        win = canvas.create_window((0, 0), window=self._body, anchor="nw")
        self._body.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width)
        )

        # Initial state
        tk.Label(
            self._body,
            text="Click  🔄 Run Scan  to check vault health.",
            font=("Segoe UI", 12),
            bg=COLOUR_BACKGROUND,
            fg=COLOUR_SUBTLE
        ).pack(pady=80)

    def _run_scan(self) -> None:
        """Execute the health scan and display results."""
        for widget in self._body.winfo_children():
            widget.destroy()

        tk.Label(
            self._body,
            text="Scanning vault...",
            font=("Segoe UI", 12),
            bg=COLOUR_BACKGROUND,
            fg=COLOUR_SUBTLE
        ).pack(pady=40)
        self.update()

        results = run_vault_health_check(self._master_password)

        for widget in self._body.winfo_children():
            widget.destroy()

        pad = {"padx": 40}

        # Overall status
        if results["vault_healthy"]:
            status_text  = "✓  Vault is Healthy"
            status_color = COLOUR_SUCCESS
        else:
            status_text  = "⚠  Issues Found"
            status_color = COLOUR_WARNING

        tk.Label(
            self._body,
            text=status_text,
            font=("Segoe UI", 20, "bold"),
            bg=COLOUR_BACKGROUND,
            fg=status_color
        ).pack(pady=(40, 4), **pad)

        tk.Label(
            self._body,
            text=f"Scanned at {results['scan_time'][:19].replace('T', ' ')}",
            font=("Segoe UI", 9),
            bg=COLOUR_BACKGROUND,
            fg=COLOUR_SUBTLE
        ).pack(pady=(0, 30), **pad)

        # Summary cards
        summary_frame = tk.Frame(self._body, bg=COLOUR_BACKGROUND)
        summary_frame.pack(fill="x", **pad, pady=(0, 24))

        self._summary_card(
            summary_frame, "Total", str(results["total_documents"]), COLOUR_TEXT
        )
        self._summary_card(
            summary_frame, "Healthy", str(results["healthy_documents"]), COLOUR_SUCCESS
        )
        self._summary_card(
            summary_frame, "Missing", str(len(results["missing_files"])),
            COLOUR_ERROR if results["missing_files"] else COLOUR_TEXT
        )
        self._summary_card(
            summary_frame, "Integrity Fails",
            str(len(results["integrity_failures"])),
            COLOUR_ERROR if results["integrity_failures"] else COLOUR_TEXT
        )
        self._summary_card(
            summary_frame, "Orphaned", str(len(results["orphaned_files"])),
            COLOUR_WARNING if results["orphaned_files"] else COLOUR_TEXT
        )
        self._summary_card(
            summary_frame, "Duplicates",
            str(len(results["duplicate_checksums"])),
            COLOUR_WARNING if results["duplicate_checksums"] else COLOUR_TEXT
        )

        # Detail sections
        self._result_section(
            "Missing Files",
            results["missing_files"],
            "All encrypted files are present.",
            COLOUR_ERROR
        )

        self._result_section(
            "Integrity Failures",
            [f"{r['name']} — {r['reason']}" for r in results["integrity_failures"]],
            "All documents passed integrity verification.",
            COLOUR_ERROR
        )

        self._result_section(
            "Orphaned Files",
            results["orphaned_files"],
            "No orphaned files found.",
            COLOUR_WARNING
        )

        self._result_section(
            "Duplicate Documents",
            [f"{r['duplicate']} duplicates {r['original']}"
             for r in results["duplicate_checksums"]],
            "No duplicate documents detected.",
            COLOUR_WARNING
        )

        # Update integrity status in database
        self._update_integrity_results(results)

        tk.Frame(self._body, bg=COLOUR_ACCENT, height=1).pack(
            fill="x", **pad, pady=(24, 0)
        )
        tk.Label(
            self._body,
            text="Scan complete. Integrity statuses updated in database.",
            font=("Segoe UI", 9),
            bg=COLOUR_BACKGROUND,
            fg=COLOUR_SUBTLE
        ).pack(pady=(8, 40), **pad)

    def _summary_card(
        self,
        parent: tk.Widget,
        label: str,
        value: str,
        colour: str
    ) -> None:
        """Render a summary statistics card."""
        card = tk.Frame(parent, bg=COLOUR_PANEL, padx=20, pady=14)
        card.pack(side="left", expand=True, fill="x", padx=6)

        tk.Label(
            card,
            text=value,
            font=("Segoe UI", 22, "bold"),
            bg=COLOUR_PANEL,
            fg=colour
        ).pack()

        tk.Label(
            card,
            text=label,
            font=("Segoe UI", 9),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack()

    def _result_section(
        self,
        title: str,
        items: list,
        empty_message: str,
        item_colour: str
    ) -> None:
        """Render a result section with a title and item list."""
        pad = {"padx": 40}

        tk.Label(
            self._body,
            text=title,
            font=("Segoe UI", 11, "bold"),
            bg=COLOUR_BACKGROUND,
            fg=COLOUR_TEXT
        ).pack(anchor="w", pady=(16, 6), **pad)

        panel = tk.Frame(self._body, bg=COLOUR_PANEL, padx=20, pady=12)
        panel.pack(fill="x", **pad)

        if not items:
            tk.Label(
                panel,
                text=f"✓  {empty_message}",
                font=("Segoe UI", 10),
                bg=COLOUR_PANEL,
                fg=COLOUR_SUCCESS
            ).pack(anchor="w")
        else:
            for item in items:
                tk.Label(
                    panel,
                    text=f"•  {item}",
                    font=("Segoe UI", 10),
                    bg=COLOUR_PANEL,
                    fg=item_colour,
                    wraplength=800,
                    justify="left"
                ).pack(anchor="w", pady=2)

    def _update_integrity_results(self, results: dict) -> None:
        """
        Update integrity_status in the database based on scan results.

        Args:
            results: The health check results dictionary.
        """
        from vaultcore.database import load_all_documents

        failed_names = {r["name"] for r in results["integrity_failures"]}
        now          = datetime.now(timezone.utc).isoformat()
        documents    = load_all_documents()

        for doc in documents:
            if doc.id is None:
                continue
            passed = doc.original_name not in failed_names
            update_integrity_status(doc.id, passed, now)

