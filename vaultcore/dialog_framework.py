"""
vaultcore/dialog_framework.py

Shared Dialog Framework for the Secure Vault Platform.

Provides consistent, reusable dialogs across all modules.
Modules must use this service instead of creating custom dialogs.
"""

import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from typing import Optional
from pathlib import Path


class DialogFramework:
    """
    Centralized dialog service for the Secure Vault Platform.

    Wraps Tkinter dialog widgets with consistent styling
    and behaviour across all modules.
    """

    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the Dialog Framework.

        Args:
            root: The main application Tk window.
        """
        self._root = root

    # ── Message dialogs ───────────────────────────────────────────────────────

    def info(self, title: str, message: str) -> None:
        """Show an informational message dialog."""
        messagebox.showinfo(title, message, parent=self._root)

    def success(self, title: str, message: str) -> None:
        """Show a success message dialog."""
        messagebox.showinfo(title, f"✓ {message}", parent=self._root)

    def warning(self, title: str, message: str) -> None:
        """Show a warning message dialog."""
        messagebox.showwarning(title, message, parent=self._root)

    def error(self, title: str, message: str) -> None:
        """Show an error message dialog."""
        messagebox.showerror(title, message, parent=self._root)

    # ── Confirmation dialogs ──────────────────────────────────────────────────

    def confirm(self, title: str, message: str) -> bool:
        """
        Show a yes/no confirmation dialog.

        Args:
            title:   The dialog title.
            message: The confirmation message.

        Returns:
            True if user clicked Yes, False if No.
        """
        return messagebox.askyesno(title, message, parent=self._root)

    def confirm_destructive(self, title: str, message: str) -> bool:
        """
        Show a destructive action confirmation.

        Adds warning styling to the message.

        Args:
            title:   The dialog title.
            message: The confirmation message.

        Returns:
            True if user confirmed.
        """
        full_message = f"⚠  {message}\n\nThis action cannot be undone."
        return messagebox.askyesno(title, full_message, parent=self._root)

    # ── Input dialogs ─────────────────────────────────────────────────────────

    def prompt_text(
        self,
        title: str,
        message: str,
        initial: str = ""
    ) -> Optional[str]:
        """
        Prompt the user for a text string.

        Args:
            title:   The dialog title.
            message: The prompt message.
            initial: Initial text value.

        Returns:
            The entered string or None if cancelled.
        """
        return simpledialog.askstring(
            title, message,
            initialvalue=initial,
            parent=self._root
        )

    def prompt_password(self, title: str, message: str) -> Optional[str]:
        """
        Prompt the user for a password.

        Args:
            title:   The dialog title.
            message: The prompt message.

        Returns:
            The entered password or None if cancelled.
        """
        return simpledialog.askstring(
            title, message,
            show="●",
            parent=self._root
        )

    # ── File dialogs ──────────────────────────────────────────────────────────

    def pick_file(
        self,
        title: str = "Select File",
        filetypes: Optional[list[tuple[str, str]]] = None
    ) -> Optional[Path]:
        """
        Open a file picker dialog.

        Args:
            title:     The dialog title.
            filetypes: Optional list of file type filters.

        Returns:
            The selected Path or None if cancelled.
        """
        if filetypes is None:
            filetypes = [("All Files", "*.*")]

        path = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            parent=self._root
        )
        return Path(path) if path else None

    def pick_files(
        self,
        title: str = "Select Files",
        filetypes: Optional[list[tuple[str, str]]] = None
    ) -> list[Path]:
        """
        Open a multi-file picker dialog.

        Args:
            title:     The dialog title.
            filetypes: Optional list of file type filters.

        Returns:
            A list of selected Paths.
        """
        if filetypes is None:
            filetypes = [("All Files", "*.*")]

        paths = filedialog.askopenfilenames(
            title=title,
            filetypes=filetypes,
            parent=self._root
        )
        return [Path(p) for p in paths] if paths else []

    def pick_folder(self, title: str = "Select Folder") -> Optional[Path]:
        """
        Open a folder picker dialog.

        Args:
            title: The dialog title.

        Returns:
            The selected folder Path or None if cancelled.
        """
        path = filedialog.askdirectory(
            title=title,
            parent=self._root
        )
        return Path(path) if path else None

    def save_as(
        self,
        title: str = "Save As",
        default_name: str = "",
        filetypes: Optional[list[tuple[str, str]]] = None
    ) -> Optional[Path]:
        """
        Open a save file dialog.

        Args:
            title:        The dialog title.
            default_name: Default filename.
            filetypes:    Optional list of file type filters.

        Returns:
            The chosen save Path or None if cancelled.
        """
        if filetypes is None:
            filetypes = [("All Files", "*.*")]

        path = filedialog.asksaveasfilename(
            title=title,
            initialfile=default_name,
            filetypes=filetypes,
            parent=self._root
        )
        return Path(path) if path else None
