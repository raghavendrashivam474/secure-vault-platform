"""
vaultcore/notifications.py

Shared notification service for the Secure Vault Platform.
All user-facing notifications should pass through this service.
"""

import tkinter as tk
from typing import Optional
from vaultcore.config import COLOURS


class NotificationService:
    """
    Provides toast-style notifications anchored to the platform window.

    Modules should never display notifications directly.
    All notifications should be routed through this service.
    """

    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the notification service.

        Args:
            root: The main application Tk window.
        """
        self._root    = root
        self._current: Optional[tk.Toplevel] = None

    def show(
        self,
        message: str,
        level: str = "info",
        duration_ms: int = 3000
    ) -> None:
        """
        Display a temporary notification toast.

        Args:
            message:     The message to display.
            level:       One of 'info', 'success', 'warning', 'error'.
            duration_ms: How long to show the notification in milliseconds.
        """
        if self._current:
            try:
                self._current.destroy()
            except Exception:
                pass

        colour_map = {
            "info":    COLOURS["accent"],
            "success": COLOURS["success"],
            "warning": COLOURS["warning"],
            "error":   COLOURS["highlight"],
        }

        bg = colour_map.get(level, COLOURS["accent"])

        toast = tk.Toplevel(self._root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=bg)

        tk.Label(
            toast,
            text=message,
            font=("Segoe UI", 10),
            bg=bg,
            fg="#ffffff",
            padx=20,
            pady=10
        ).pack()

        # Position bottom right of root window
        self._root.update_idletasks()
        rx = self._root.winfo_x() + self._root.winfo_width()
        ry = self._root.winfo_y() + self._root.winfo_height()
        toast.geometry(f"+{rx - 320}+{ry - 80}")

        self._current = toast
        self._root.after(duration_ms, self._dismiss)

    def _dismiss(self) -> None:
        """Dismiss the current notification."""
        if self._current:
            try:
                self._current.destroy()
            except Exception:
                pass
            self._current = None

    def info(self, message: str) -> None:
        """Show an info notification."""
        self.show(message, level="info")

    def success(self, message: str) -> None:
        """Show a success notification."""
        self.show(message, level="success")

    def warning(self, message: str) -> None:
        """Show a warning notification."""
        self.show(message, level="warning")

    def error(self, message: str) -> None:
        """Show an error notification."""
        self.show(message, level="error")

