"""
ProgressOverlayService
----------------------
Subscribes to the ExecutionEngine's EventDispatcher and manages
one ProgressOverlay window per active task.

Modules do NOT create overlays themselves.
They simply submit an ExecutionRequest — the overlay appears automatically.

Lifecycle
---------
  ExecutionStartedEvent    → create ProgressOverlay
  ProgressUpdatedEvent     → refresh visible fields
  ExecutionCompletedEvent  → close overlay
  ExecutionFailedEvent     → close overlay
  ExecutionCancelledEvent  → close overlay

All UI mutations are marshalled to the main thread via parent.after(0, ...).
Handlers themselves run on worker threads.
"""

import tkinter as tk
from typing import Dict, Optional

from vaultcore.execution.engine.execution_engine import ExecutionEngine
from vaultcore.execution.events.execution_events import (
    ExecutionStartedEvent,
    ProgressUpdatedEvent,
    ExecutionCompletedEvent,
    ExecutionFailedEvent,
    ExecutionCancelledEvent,
)
from vaultcore.execution.ui.progress_overlay import ProgressOverlay


class ProgressOverlayService:
    """Auto-manages progress overlays for the ExecutionEngine."""

    def __init__(
        self,
        root: tk.Tk,
        engine: ExecutionEngine,
        min_task_seconds_before_show: float = 0.0,
    ) -> None:
        self._root   = root
        self._engine = engine

        # Optional threshold — future use, defaults to always show
        self._min_task_seconds_before_show = min_task_seconds_before_show

        # execution_id → overlay
        self._overlays: Dict[str, ProgressOverlay] = {}

        self._subscribe()

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    def _subscribe(self) -> None:
        d = self._engine.dispatcher
        d.subscribe(ExecutionStartedEvent,   self._on_started_worker)
        d.subscribe(ProgressUpdatedEvent,    self._on_progress_worker)
        d.subscribe(ExecutionCompletedEvent, self._on_completed_worker)
        d.subscribe(ExecutionFailedEvent,    self._on_failed_worker)
        d.subscribe(ExecutionCancelledEvent, self._on_cancelled_worker)

    # ------------------------------------------------------------------
    # Worker-thread entry points — marshal to main thread
    # ------------------------------------------------------------------

    def _on_started_worker(self, event: ExecutionStartedEvent) -> None:
        self._root.after(0, lambda: self._on_started(event))

    def _on_progress_worker(self, event: ProgressUpdatedEvent) -> None:
        self._root.after(0, lambda: self._on_progress(event))

    def _on_completed_worker(self, event: ExecutionCompletedEvent) -> None:
        self._root.after(0, lambda: self._close(event.task.execution_id))

    def _on_failed_worker(self, event: ExecutionFailedEvent) -> None:
        self._root.after(0, lambda: self._close(event.task.execution_id))

    def _on_cancelled_worker(self, event: ExecutionCancelledEvent) -> None:
        self._root.after(0, lambda: self._close(event.task.execution_id))

    # ------------------------------------------------------------------
    # Main-thread handlers
    # ------------------------------------------------------------------

    def _on_started(self, event: ExecutionStartedEvent) -> None:
        task = event.task
        exec_id = task.execution_id

        # Never duplicate
        if exec_id in self._overlays:
            return

        overlay = ProgressOverlay(parent=self._root, task_name=task.task_name)
        self._overlays[exec_id] = overlay

        # Center relative to root
        self._center_over_root(overlay)

    def _on_progress(self, event: ProgressUpdatedEvent) -> None:
        overlay = self._overlays.get(event.execution_id)
        if overlay is None:
            return
        try:
            overlay.update_progress(event.progress)
        except tk.TclError:
            # Window was destroyed — drop reference
            self._overlays.pop(event.execution_id, None)

    def _close(self, execution_id: str) -> None:
        overlay = self._overlays.pop(execution_id, None)
        if overlay is None:
            return
        overlay.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _center_over_root(self, overlay: ProgressOverlay) -> None:
        try:
            self._root.update_idletasks()
            rx = self._root.winfo_rootx()
            ry = self._root.winfo_rooty()
            rw = self._root.winfo_width()
            rh = self._root.winfo_height()

            ow = overlay.winfo_reqwidth()
            oh = overlay.winfo_reqheight()

            x = rx + (rw // 2) - (ow // 2)
            y = ry + (rh // 3) - (oh // 2)
            overlay.geometry(f"+{x}+{y}")
        except Exception:
            pass
