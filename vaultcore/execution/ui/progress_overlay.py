"""
ProgressOverlay
---------------
A single floating dialog that visualizes execution progress.

Owned by ProgressOverlayService.
Never instantiated by modules directly.

Design
------
  - Small, centered Toplevel
  - Non-modal (user can still lock, exit, etc.)
  - Auto-updates from ProgressUpdatedEvent
  - Auto-dismisses on completion / failure / cancellation
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from vaultcore.execution.progress.progress_model import ProgressModel


class ProgressOverlay(tk.Toplevel):
    """Floating progress dialog for a single execution task."""

    def __init__(self, parent: tk.Widget, task_name: str) -> None:
        super().__init__(parent)

        self.title(task_name)
        self.geometry("460x180")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")
        self.transient(parent)

        # Don't grab focus — keep it non-blocking
        self.attributes("-topmost", True)

        self._build(task_name)

    def _build(self, task_name: str) -> None:
        # Title
        tk.Label(
            self,
            text=task_name,
            font=("Segoe UI", 12, "bold"),
            bg="#1a1a2e",
            fg="#ffffff"
        ).pack(pady=(18, 4), padx=20, anchor="w")

        # Step label
        self._step_label = tk.Label(
            self,
            text="Preparing...",
            font=("Segoe UI", 10),
            bg="#1a1a2e",
            fg="#9aa4c7"
        )
        self._step_label.pack(padx=20, anchor="w")

        # Progress bar
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Vault.Horizontal.TProgressbar",
            troughcolor="#0f0f1a",
            background="#4a9eff",
            bordercolor="#0f0f1a",
            lightcolor="#4a9eff",
            darkcolor="#4a9eff",
        )

        self._progress = ttk.Progressbar(
            self,
            style="Vault.Horizontal.TProgressbar",
            mode="determinate",
            length=420,
            maximum=100.0,
        )
        self._progress.pack(padx=20, pady=(10, 6))

        # Message row
        self._message_label = tk.Label(
            self,
            text="",
            font=("Segoe UI", 9),
            bg="#1a1a2e",
            fg="#6b7599",
            anchor="w",
            wraplength=420,
            justify="left",
        )
        self._message_label.pack(padx=20, fill="x", anchor="w")

        # Counts row
        self._counts_label = tk.Label(
            self,
            text="",
            font=("Segoe UI", 9),
            bg="#1a1a2e",
            fg="#6b7599",
        )
        self._counts_label.pack(padx=20, pady=(4, 12), anchor="w")

    # ------------------------------------------------------------------
    # Public API — called by ProgressOverlayService on main thread
    # ------------------------------------------------------------------

    def update_progress(self, model: ProgressModel) -> None:
        """Refresh all visible fields from a ProgressModel snapshot."""
        # Step
        step = model.current_step or "Working"
        self._step_label.config(text=step)

        # Bar
        if model.items_total > 0:
            self._progress.config(mode="determinate", maximum=100.0)
            self._progress["value"] = max(0.0, min(100.0, model.percentage))
        else:
            # Indeterminate — bounce the bar
            if str(self._progress["mode"]) != "indeterminate":
                self._progress.config(mode="indeterminate")
                self._progress.start(80)

        # Message
        self._message_label.config(text=model.status_message or "")

        # Counts
        if model.items_total > 0:
            counts = f"{model.items_processed:,} / {model.items_total:,}   ({model.percentage:.1f}%)"
        elif model.items_processed > 0:
            counts = f"{model.items_processed:,} processed"
        else:
            counts = ""

        if model.elapsed_seconds > 0:
            counts = (counts + "   " if counts else "") + f"elapsed {model.elapsed_seconds:.1f}s"

        self._counts_label.config(text=counts)

    def close(self) -> None:
        """Stop any animations and destroy the dialog."""
        try:
            self._progress.stop()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
