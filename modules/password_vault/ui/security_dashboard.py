"""
modules/password_vault/ui/security_dashboard.py

Password Vault security dashboard.

Displays audit findings and vault hygiene score.
All calculations happen in the audit engine, not here.
"""

import tkinter as tk
from typing import Callable

from vaultcore.theme import Theme
from vaultcore.event_bus import platform_bus

from modules.password_vault.core.database import load_all_passwords
from modules.password_vault.core.security_audit import (
    run_audit, calculate_hygiene_score
)
from modules.password_vault.models.audit_result import AuditResult, AuditFinding
from modules.password_vault.ui.password_editor import decrypt_file_to_memory_string


SEVERITY_COLOURS = {
    "critical": Theme.ERROR,
    "warning":  Theme.WARNING,
    "info":     Theme.ACCENT,
}

SEVERITY_ICONS = {
    "critical": "🔴",
    "warning":  "🟡",
    "info":     "🔵",
}

FINDING_LABELS = {
    "weak":          "Weak Password",
    "reused":        "Reused Password",
    "aging":         "Aging Password",
    "old":           "Old Password",
    "critical_age":  "Critical Age",
    "common":        "Common Password",
}


class SecurityDashboard(tk.Toplevel):
    """
    Vault-wide security dashboard.

    Shows audit metrics and hygiene score.
    Findings are grouped by severity.
    """

    def __init__(
        self,
        parent: tk.Widget,
        master_password: str,
        notifications,
        activity_service
    ) -> None:
        super().__init__(parent)
        self.title("Password Vault Security")
        self.geometry("780x600")
        self.configure(bg=Theme.BACKGROUND)
        self.grab_set()

        self._master_password  = master_password
        self._notifications    = notifications
        self._activity_service = activity_service
        self._result: AuditResult = None

        self._build()
        self._run_audit_and_render()

    def _build(self) -> None:
        # Header
        header = tk.Frame(self, bg=Theme.PANEL, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🛡  Vault Security Dashboard",
            font=Theme.FONT_HEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left", padx=20, pady=12)

        tk.Button(
            header,
            text="🔄  Rescan",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._run_audit_and_render
        ).pack(side="right", padx=16, pady=12)

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

    def _run_audit_and_render(self) -> None:
        """Execute audit and render results."""
        for widget in self._body.winfo_children():
            widget.destroy()

        # Loading indicator
        tk.Label(
            self._body,
            text="🔍  Scanning vault...",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(pady=40)
        self.update()

        # Run audit
        entries = load_all_passwords()
        self._result = run_audit(
            entries, self._master_password, decrypt_file_to_memory_string
        )

        # Publish event
        platform_bus.publish("password.audit_completed", {
            "total":    self._result.total_credentials,
            "findings": len(self._result.findings)
        })

        # Log activity
        self._activity_service.record(
            "SecurityAudit", "password_vault",
            f"{len(self._result.findings)} findings"
        )

        # Render results
        for widget in self._body.winfo_children():
            widget.destroy()

        self._render_score()
        self._render_metrics()
        self._render_findings()

    def _render_score(self) -> None:
        """Render the vault hygiene score."""
        score = calculate_hygiene_score(self._result)

        if score >= 80:
            color = Theme.SUCCESS
            grade = "Excellent"
        elif score >= 60:
            color = Theme.WARNING
            grade = "Good"
        elif score >= 40:
            color = Theme.WARNING
            grade = "Fair"
        else:
            color = Theme.ERROR
            grade = "Poor"

        score_frame = tk.Frame(self._body, bg=Theme.PANEL, padx=24, pady=20)
        score_frame.pack(fill="x", padx=20, pady=(20, 12))

        tk.Label(
            score_frame,
            text="Vault Hygiene Score",
            font=Theme.FONT_LABEL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w")

        score_row = tk.Frame(score_frame, bg=Theme.PANEL)
        score_row.pack(anchor="w", pady=(4, 0))

        tk.Label(
            score_row,
            text=f"{score}",
            font=("Segoe UI", 40, "bold"),
            bg=Theme.PANEL,
            fg=color
        ).pack(side="left")

        tk.Label(
            score_row,
            text="/100",
            font=("Segoe UI", 16),
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(side="left", padx=(4, 12), pady=(14, 0))

        tk.Label(
            score_row,
            text=f"● {grade}",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=color
        ).pack(side="left", pady=(14, 0))

        # Scan timestamp
        scanned = self._result.generated_at[:19].replace("T", " ")
        tk.Label(
            score_frame,
            text=f"Last scan: {scanned}",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(8, 0))

    def _render_metrics(self) -> None:
        """Render metric cards."""
        metrics_container = tk.Frame(self._body, bg=Theme.BACKGROUND)
        metrics_container.pack(fill="x", padx=20, pady=8)

        cards = [
            ("Total",    self._result.total_credentials,   Theme.TEXT),
            ("Strong",   self._result.strong_count,        Theme.SUCCESS),
            ("Weak",     self._result.weak_count,          Theme.ERROR),
            ("Reused",   self._result.reused_count,        Theme.WARNING),
            ("Aging",    self._result.aging_count,         Theme.WARNING),
            ("Old",      self._result.old_count,           Theme.WARNING),
            ("Critical", self._result.critical_age_count,  Theme.ERROR),
            ("Common",   self._result.common_count,        Theme.ERROR),
        ]

        for label, value, colour in cards:
            card = tk.Frame(metrics_container, bg=Theme.PANEL, padx=12, pady=10)
            card.pack(side="left", expand=True, fill="x", padx=3)

            tk.Label(
                card,
                text=str(value),
                font=("Segoe UI", 18, "bold"),
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

    def _render_findings(self) -> None:
        """Render all findings grouped by severity."""
        tk.Label(
            self._body,
            text=f"Findings ({len(self._result.findings)})",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(anchor="w", padx=20, pady=(20, 8))

        if not self._result.findings:
            tk.Label(
                self._body,
                text="✓  No security issues detected.",
                font=Theme.FONT_BODY,
                bg=Theme.BACKGROUND,
                fg=Theme.SUCCESS
            ).pack(anchor="w", padx=20, pady=(0, 20))
            return

        # Sort findings: critical first, then warning, then info
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        sorted_findings = sorted(
            self._result.findings,
            key=lambda f: severity_order.get(f.severity, 3)
        )

        for finding in sorted_findings:
            self._render_finding(finding)

    def _render_finding(self, finding: AuditFinding) -> None:
        """Render a single audit finding."""
        colour = SEVERITY_COLOURS.get(finding.severity, Theme.SUBTLE)
        icon   = SEVERITY_ICONS.get(finding.severity, "●")
        label  = FINDING_LABELS.get(finding.finding_type, finding.finding_type)

        row = tk.Frame(self._body, bg=Theme.PANEL, padx=16, pady=10)
        row.pack(fill="x", padx=20, pady=3)

        header_row = tk.Frame(row, bg=Theme.PANEL)
        header_row.pack(fill="x", anchor="w")

        tk.Label(
            header_row,
            text=icon,
            font=("Segoe UI", 12),
            bg=Theme.PANEL,
            fg=colour
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            header_row,
            text=finding.entry_title,
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left")

        tk.Label(
            header_row,
            text=f"  ●  {label}",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=colour
        ).pack(side="left")

        tk.Label(
            row,
            text=finding.detail,
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(4, 0), padx=(20, 0))
