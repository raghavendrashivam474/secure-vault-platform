"""
vaultcore/activity_monitor.py

Idle Activity Monitor for the Secure Vault Platform.

Observes user interaction events and triggers
auto-lock when the idle threshold is exceeded.
"""

import tkinter as tk
from typing import Optional, Callable
from vaultcore.logger import log_event, log_info
from vaultcore.session import SessionManager


class ActivityMonitor:
    """
    Monitors user activity and enforces auto-lock policy.

    Binds to keyboard, mouse, and window events on the
    root Tkinter window. Resets the idle timer on every
    detected interaction. Triggers the lock callback when
    the idle threshold is exceeded.
    """

    def __init__(
        self,
        root: tk.Tk,
        session_manager: SessionManager,
        on_lock: Callable
    ) -> None:
        """
        Initialize the activity monitor.

        Args:
            root:            The main application Tk window.
            session_manager: The platform session manager.
            on_lock:         Callback invoked when auto-lock triggers.
        """
        self._root            = root
        self._session_manager = session_manager
        self._on_lock         = on_lock
        self._timer_id:       Optional[str] = None
        self._idle_seconds:   int = 0

        self._bind_events()

    def _bind_events(self) -> None:
        """Bind activity detection events to the root window."""
        for event in ("<Motion>", "<KeyPress>", "<ButtonPress>", "<MouseWheel>"):
            self._root.bind_all(
                event,
                lambda e: self._on_activity(),
                add="+"
            )

    def _on_activity(self) -> None:
        """Handle a detected user activity event."""
        self._session_manager.update_activity()

    def set_idle_timeout(self, seconds: int) -> None:
        """
        Set the idle timeout and start monitoring.

        Args:
            seconds: Idle seconds before auto-lock triggers.
                     0 disables auto-lock.
        """
        self._idle_seconds = seconds
        self._cancel_timer()

        if seconds > 0:
            self._schedule_check()
            log_info(f"Auto-lock set to {seconds} seconds.")
        else:
            log_info("Auto-lock disabled.")

    def _schedule_check(self) -> None:
        """Schedule the next idle check."""
        self._timer_id = self._root.after(10000, self._check_idle)

    def _cancel_timer(self) -> None:
        """Cancel any running idle check timer."""
        if self._timer_id:
            try:
                self._root.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

    def _check_idle(self) -> None:
        """
        Check whether the idle threshold has been exceeded.

        Called every 10 seconds by the Tkinter scheduler.
        """
        if not self._session_manager.is_authenticated():
            return

        session = self._session_manager.get_session()
        if session is None:
            return

        if session.idle_seconds() >= self._idle_seconds:
            log_event("AutoLock", f"Idle for {self._idle_seconds}s")
            self._session_manager.lock()
            self._on_lock()
        else:
            self._schedule_check()

    def stop(self) -> None:
        """Stop the activity monitor."""
        self._cancel_timer()
