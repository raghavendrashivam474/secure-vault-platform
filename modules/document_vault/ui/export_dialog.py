"""
ui/export_dialog.py

Export dialog for the Personal Document Vault.
Handles single, multi, category, and full vault export
with progress indication and result summary.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional

from modules.document_vault.core.export import (
    export_document,
    export_documents,
    export_category,
    export_vault
)
from modules.document_vault.models.document import Document
from modules.document_vault.models.category import Category


COLOUR_BACKGROUND = "#1a1a2e"
COLOUR_PANEL      = "#16213e"
COLOUR_ACCENT     = "#0f3460"
COLOUR_HIGHLIGHT  = "#e94560"
COLOUR_TEXT       = "#eaeaea"
COLOUR_SUBTLE     = "#a0a0b0"
COLOUR_SUCCESS    = "#51cf66"
COLOUR_ERROR      = "#ff6b6b"


def export_single_document(
    parent: tk.Widget,
    document: Document,
    master_password: str
) -> None:
    """
    Prompt for a save location and export a single document.

    Args:
        parent:          The parent widget for dialogs.
        document:        The Document to export.
        master_password: The master password for decryption.
    """
    folder_str = filedialog.askdirectory(
        title  = f"Export '{document.original_name}' to...",
        parent = parent
    )

    if not folder_str:
        return

    destination = Path(folder_str)
    success, message = export_document(document, destination, master_password)

    if success:
        messagebox.showinfo(
            "Export Complete",
            f"Document exported successfully.\n\n{message}",
            parent=parent
        )
    else:
        messagebox.showerror(
            "Export Failed",
            message,
            parent=parent
        )


def export_selected_documents(
    parent: tk.Widget,
    documents: list[Document],
    master_password: str
) -> None:
    """
    Prompt for a folder and export multiple selected documents.

    Args:
        parent:          The parent widget for dialogs.
        documents:       List of Documents to export.
        master_password: The master password for decryption.
    """
    if not documents:
        messagebox.showinfo(
            "No Documents",
            "No documents selected for export.",
            parent=parent
        )
        return

    folder_str = filedialog.askdirectory(
        title  = f"Export {len(documents)} document(s) to...",
        parent = parent
    )

    if not folder_str:
        return

    destination = Path(folder_str)

    # Progress window
    progress_win = _build_progress_window(parent, len(documents))

    def update_progress(current: int, total: int, filename: str) -> None:
        progress_win["label"].config(
            text=f"Exporting {current} of {total}:\n{filename}"
        )
        progress_win["bar"]["value"] = int((current / total) * 100)
        progress_win["window"].update()

    result = export_documents(
        documents          = documents,
        destination_folder = destination,
        master_password    = master_password,
        progress_callback  = update_progress
    )

    progress_win["window"].destroy()
    _show_export_result(parent, result)


def export_category_documents(
    parent: tk.Widget,
    category: Category,
    master_password: str
) -> None:
    """
    Export all documents belonging to a category.

    Args:
        parent:          The parent widget for dialogs.
        category:        The Category whose documents to export.
        master_password: The master password for decryption.
    """
    folder_str = filedialog.askdirectory(
        title  = f"Export category '{category.name}' to...",
        parent = parent
    )

    if not folder_str:
        return

    destination = Path(folder_str)

    progress_win = _build_progress_window(
        parent, category.document_count
    )

    def update_progress(current: int, total: int, filename: str) -> None:
        if total > 0:
            progress_win["label"].config(
                text=f"Exporting {current} of {total}:\n{filename}"
            )
            progress_win["bar"]["value"] = int((current / total) * 100)
            progress_win["window"].update()

    result = export_category(
        category_id        = category.id,
        category_name      = category.name,
        destination_folder = destination,
        master_password    = master_password,
        progress_callback  = update_progress
    )

    progress_win["window"].destroy()
    _show_export_result(parent, result)


def export_entire_vault(
    parent: tk.Widget,
    master_password: str,
    total_documents: int
) -> None:
    """
    Export all documents in the vault preserving category structure.

    Args:
        parent:           The parent widget for dialogs.
        master_password:  The master password for decryption.
        total_documents:  Total number of documents for progress display.
    """
    confirmed = messagebox.askyesno(
        "Export Entire Vault",
        f"This will export all {total_documents} document(s) to a folder "
        f"you choose.\n\n"
        f"Documents will be organized into category subfolders.\n\n"
        f"Continue?",
        parent=parent
    )

    if not confirmed:
        return

    folder_str = filedialog.askdirectory(
        title  = "Choose Export Destination",
        parent = parent
    )

    if not folder_str:
        return

    destination  = Path(folder_str)
    progress_win = _build_progress_window(parent, total_documents)

    def update_progress(current: int, total: int, filename: str) -> None:
        if total > 0:
            progress_win["label"].config(
                text=f"Exporting {current} of {total}:\n{filename}"
            )
            progress_win["bar"]["value"] = int((current / total) * 100)
            progress_win["window"].update()

    result = export_vault(
        destination_folder  = destination,
        master_password     = master_password,
        preserve_categories = True,
        progress_callback   = update_progress
    )

    progress_win["window"].destroy()

    export_path = result.get("export_path", "")
    _show_export_result(parent, result, export_path)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_progress_window(
    parent: tk.Widget,
    total: int
) -> dict:
    """
    Build a simple progress indicator window.

    Args:
        parent: The parent widget.
        total:  Total number of items to process.

    Returns:
        A dict with window, label, and bar references.
    """
    from tkinter import ttk

    win = tk.Toplevel(parent)
    win.title("Exporting...")
    win.geometry("400x140")
    win.resizable(False, False)
    win.configure(bg=COLOUR_PANEL)
    win.grab_set()

    label = tk.Label(
        win,
        text="Preparing export...",
        font=("Segoe UI", 10),
        bg=COLOUR_PANEL,
        fg=COLOUR_TEXT,
        wraplength=360
    )
    label.pack(pady=(20, 10), padx=20)

    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Export.Horizontal.TProgressbar",
        troughcolor=COLOUR_BACKGROUND,
        background=COLOUR_HIGHLIGHT,
        bordercolor=COLOUR_ACCENT,
        lightcolor=COLOUR_HIGHLIGHT,
        darkcolor=COLOUR_HIGHLIGHT
    )

    bar = ttk.Progressbar(
        win,
        style  = "Export.Horizontal.TProgressbar",
        orient = "horizontal",
        length = 360,
        mode   = "determinate",
        maximum = 100
    )
    bar.pack(pady=(0, 20), padx=20)

    return {"window": win, "label": label, "bar": bar}


def _show_export_result(
    parent: tk.Widget,
    result: dict,
    export_path: str = ""
) -> None:
    """
    Display the export result summary to the user.

    Args:
        parent:      The parent widget.
        result:      The export result dictionary.
        export_path: Optional path to the export folder.
    """
    total   = result["total"]
    success = result["success"]
    failed  = result["failed"]

    if total == 0:
        messagebox.showinfo(
            "Export Complete",
            "No documents were found to export.",
            parent=parent
        )
        return

    if failed == 0:
        message = f"All {success} document(s) exported successfully."
        if export_path:
            message += f"\n\nLocation:\n{export_path}"
        messagebox.showinfo("Export Complete", message, parent=parent)
    else:
        failures = "\n".join(f"  • {name}" for name in result["failures"])
        message  = (
            f"Export completed with errors.\n\n"
            f"Exported:  {success}\n"
            f"Failed:    {failed}\n\n"
            f"Failed documents:\n{failures}"
        )
        if export_path:
            message += f"\n\nLocation:\n{export_path}"
        messagebox.showwarning("Export Partial", message, parent=parent)

