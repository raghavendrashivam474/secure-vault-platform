"""
core/vault.py

Vault state management and auto-lock functionality
for the Personal Document Vault.
"""

import tkinter as tk
from typing import Optional, Callable
from vaultcore.database import vault_exists


# Auto-lock timeout options
# Key is display label, value is milliseconds
AUTO_LOCK_OPTIONS: dict[str, int] = {
    "Never":       0,
    "30 seconds":  30,
    "1 minute":    60,
    "2 minutes":   120,
    "5 minutes":   300,
    "10 minutes":  600,
    "15 minutes":  900,
    "30 minutes":  1800,
}


class VaultState:
    """
    Manages the lock state and auto-lock timer for the vault.

    The vault starts locked. It unlocks after authentication.
    If auto-lock is configured, the vault locks automatically
    after the specified period of inactivity.
    """

    def __init__(self) -> None:
        """Initialize the vault in a locked state."""
        self._unlocked:          bool              = False
        self._auto_lock_seconds: int               = 0
        self._timer_id:          Optional[str]     = None
        self._root:              Optional[tk.Tk]   = None
        self._on_lock_callback:  Optional[Callable] = None

    def set_root(self, root: tk.Tk) -> None:
        """
        Set the Tkinter root window for timer scheduling.

        Args:
            root: The main application Tk window.
        """
        self._root = root

    def set_lock_callback(self, callback: Callable) -> None:
        """
        Set the callback to invoke when auto-lock triggers.

        Args:
            callback: Function to call when the vault auto-locks.
        """
        self._on_lock_callback = callback

    def set_auto_lock(self, seconds: int) -> None:
        """
        Configure the auto-lock timeout in seconds.

        Args:
            seconds: Seconds of inactivity before locking.
                     0 disables auto-lock.
        """
        self._auto_lock_seconds = seconds
        self._reset_timer()

    def unlock(self) -> None:
        """Set the vault state to unlocked and start the auto-lock timer."""
        self._unlocked = True
        self._reset_timer()

    def lock(self) -> None:
        """Set the vault state to locked and cancel any running timer."""
        self._unlocked = False
        self._cancel_timer()

    def is_unlocked(self) -> bool:
        """Return True if the vault is currently unlocked."""
        return self._unlocked

    def is_locked(self) -> bool:
        """Return True if the vault is currently locked."""
        return not self._unlocked

    def reset_activity(self) -> None:
        """
        Reset the auto-lock timer due to user activity.

        Call this whenever the user interacts with the application.
        """
        if self._unlocked:
            self._reset_timer()

    def _reset_timer(self) -> None:
        """Cancel any existing timer and start a fresh one."""
        self._cancel_timer()

        if (
            self._auto_lock_seconds > 0
            and self._unlocked
            and self._root is not None
        ):
            ms = self._auto_lock_seconds * 1000
            self._timer_id = self._root.after(ms, self._trigger_auto_lock)

    def _cancel_timer(self) -> None:
        """Cancel the running auto-lock timer if one exists."""
        if self._timer_id is not None and self._root is not None:
            try:
                self._root.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

    def _trigger_auto_lock(self) -> None:
        """Invoke auto-lock after the timer expires."""
        if self._unlocked:
            self.lock()
            if self._on_lock_callback:
                self._on_lock_callback()


def check_vault_exists() -> bool:
    """
    Check whether a vault has been created on this machine.

    Returns:
        True if a vault configuration exists.
    """
    return vault_exists()

