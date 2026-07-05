"""
ui/import_dialog.py

File picker dialog for the Personal Document Vault.
Responsible only for presenting the file selection dialog
and returning the chosen path.

No encryption, metadata extraction, or business logic
should exist in this module.
"""

from pathlib import Path
from tkinter import filedialog
from typing import Optional


# Supported file type filters for the file dialog
FILE_TYPE_FILTERS: list[tuple[str, str]] = [
    ("Supported Documents", "*.pdf *.png *.jpg *.jpeg *.webp"),
    ("PDF Files",           "*.pdf"),
    ("Image Files",         "*.png *.jpg *.jpeg *.webp"),
    ("All Files",           "*.*"),
]


def open_file_dialog() -> Optional[Path]:
    """
    Open a standard file selection dialog.

    Presents the user with a filtered file browser.
    Returns the selected file path or None if cancelled.

    Returns:
        A Path object pointing to the selected file,
        or None if the user cancelled the dialog.
    """
    selected = filedialog.askopenfilename(
        title       = "Select a Document to Import",
        filetypes   = FILE_TYPE_FILTERS
    )

    if not selected:
        return None

    return Path(selected)

