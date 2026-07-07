"""
vaultcore/clipboard_manager.py

Centralized Clipboard Manager for the Secure Vault Platform.

All modules must use this service for clipboard operations.
No module should access the operating system clipboard directly.
"""

import tkinter as tk
from typing import Optional
from vaultcore.logger import log_event, log_debug


class ClipboardManager:
    """
    Centralized clipboard access for the Secure Vault Platform.

    Provides a safe abstraction over the OS clipboard.
    Supports secure clearing for sensitive data.
    """

    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the Clipboard Manager.

        Args:
            root: The main application Tk window.
        """
        self._root                = root
        self._last_copied:  str   = ""
        self._auto_clear_id: Optional[str] = None

    def copy_text(
        self,
        text: str,
        module_id: str = "platform",
        auto_clear_seconds: int = 0
    ) -> bool:
        """
        Copy text to the system clipboard.

        Args:
            text:               The text to copy.
            module_id:          The requesting module.
            auto_clear_seconds: If greater than 0, clear clipboard
                                after this many seconds.

        Returns:
            True if the copy succeeded.
        """
        try:
            self._root.clipboard_clear()
            self._root.clipboard_append(text)
            self._root.update()
            self._last_copied = text

            log_event("ClipboardCopy", f"{module_id}: {len(text)} chars")

            if auto_clear_seconds > 0:
                self._schedule_clear(auto_clear_seconds)

            return True
        except Exception as error:
            log_debug(f"[Clipboard] Copy failed: {error}")
            return False

    def copy_path(self, path: str, module_id: str = "platform") -> bool:
        """
        Copy a file path to the clipboard.

        Args:
            path:      The file path string.
            module_id: The requesting module.

        Returns:
            True if the copy succeeded.
        """
        return self.copy_text(path, module_id)

    def clear(self) -> None:
        """
        Clear the system clipboard immediately.

        Used for security-sensitive operations.
        """
        try:
            self._root.clipboard_clear()
            self._root.update()
            self._last_copied = ""
            log_event("ClipboardCleared")
        except Exception:
            pass

    def _schedule_clear(self, seconds: int) -> None:
        """Schedule automatic clipboard clearing."""
        if self._auto_clear_id:
            try:
                self._root.after_cancel(self._auto_clear_id)
            except Exception:
                pass

        self._auto_clear_id = self._root.after(
            seconds * 1000, self._auto_clear
        )

    def _auto_clear(self) -> None:
        """Automatically clear the clipboard after timeout."""
        self.clear()
        self._auto_clear_id = None
