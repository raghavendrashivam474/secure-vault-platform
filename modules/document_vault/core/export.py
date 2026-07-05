"""
core/export.py

Document export functionality for the Personal Document Vault.
Handles single document export, multi-document export,
category export, and full vault export.

All exports decrypt documents in memory and write
plaintext files to the user-specified destination.
No temporary files are created during the process.
"""

from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from vaultcore.encryption import decrypt_file_to_memory
from vaultcore.database import load_all_documents, load_all_categories
from modules.document_vault.models.document import Document
from vaultcore.file_utils import VAULT_ENCRYPTED_PATH


# ── Single document export ────────────────────────────────────────────────────

def export_document(
    document: Document,
    destination_folder: Path,
    master_password: str
) -> tuple[bool, str]:
    """
    Export a single document to the destination folder.

    Decrypts the document in memory and writes the
    plaintext file using the original display name.

    Args:
        document:           The Document object to export.
        destination_folder: The folder to write the exported file into.
        master_password:    The master password for decryption.

    Returns:
        A tuple of (success, message).
    """
    encrypted_path = VAULT_ENCRYPTED_PATH / document.encrypted_name

    if not encrypted_path.exists():
        return False, f"Encrypted file not found for '{document.original_name}'."

    decrypted_bytes = decrypt_file_to_memory(encrypted_path, master_password)

    if decrypted_bytes is None:
        return False, f"Decryption failed for '{document.original_name}'."

    try:
        destination_folder.mkdir(parents=True, exist_ok=True)
        output_path = _resolve_output_path(destination_folder, document.original_name)
        output_path.write_bytes(decrypted_bytes)
        return True, str(output_path)
    except Exception as error:
        return False, f"Failed to write '{document.original_name}': {error}"


# ── Multi-document export ─────────────────────────────────────────────────────

def export_documents(
    documents: list[Document],
    destination_folder: Path,
    master_password: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> dict:
    """
    Export multiple documents to the destination folder.

    Args:
        documents:           List of Document objects to export.
        destination_folder:  The folder to write exported files into.
        master_password:     The master password for decryption.
        progress_callback:   Optional callback(current, total, filename)
                             called after each document is processed.

    Returns:
        A summary dictionary with success count, failure count,
        and a list of failed document names.
    """
    total    = len(documents)
    success  = 0
    failures = []

    for index, document in enumerate(documents, start=1):
        if progress_callback:
            progress_callback(index, total, document.original_name)

        ok, message = export_document(
            document, destination_folder, master_password
        )

        if ok:
            success += 1
        else:
            failures.append(document.original_name)
            print(f"[Export] Failed: {message}")

    return {
        "total":    total,
        "success":  success,
        "failed":   len(failures),
        "failures": failures
    }


# ── Category export ───────────────────────────────────────────────────────────

def export_category(
    category_id: int,
    category_name: str,
    destination_folder: Path,
    master_password: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> dict:
    """
    Export all documents belonging to a specific category.

    Creates a subfolder named after the category inside
    the destination folder.

    Args:
        category_id:         The category primary key.
        category_name:       The category display name.
        destination_folder:  The root export folder.
        master_password:     The master password for decryption.
        progress_callback:   Optional progress callback.

    Returns:
        A summary dictionary.
    """
    all_documents = load_all_documents()
    category_docs = [
        d for d in all_documents if d.category_id == category_id
    ]

    if not category_docs:
        return {
            "total": 0, "success": 0, "failed": 0, "failures": []
        }

    category_folder = destination_folder / _sanitize_folder_name(category_name)

    return export_documents(
        documents          = category_docs,
        destination_folder = category_folder,
        master_password    = master_password,
        progress_callback  = progress_callback
    )


# ── Full vault export ─────────────────────────────────────────────────────────

def export_vault(
    destination_folder: Path,
    master_password: str,
    preserve_categories: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> dict:
    """
    Export every document stored in the vault.

    When preserve_categories is True, documents are organized
    into subfolders matching their category names.
    Uncategorized documents are placed in an Uncategorized folder.

    Args:
        destination_folder:  The root export folder.
        master_password:     The master password for decryption.
        preserve_categories: Organize output by category.
        progress_callback:   Optional progress callback.

    Returns:
        A summary dictionary with export statistics.
    """
    all_documents = load_all_documents()
    all_categories = {c.id: c.name for c in load_all_categories()}

    total    = len(all_documents)
    success  = 0
    failures = []

    timestamp   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    export_root = destination_folder / f"VaultExport_{timestamp}"
    export_root.mkdir(parents=True, exist_ok=True)

    for index, document in enumerate(all_documents, start=1):
        if progress_callback:
            progress_callback(index, total, document.original_name)

        if preserve_categories and document.category_id is not None:
            cat_name    = all_categories.get(document.category_id, "Uncategorized")
            output_dir  = export_root / _sanitize_folder_name(cat_name)
        else:
            output_dir = export_root / "Uncategorized"

        ok, message = export_document(document, output_dir, master_password)

        if ok:
            success += 1
        else:
            failures.append(document.original_name)
            print(f"[Export] Failed: {message}")

    # Write export summary
    _write_export_summary(export_root, total, success, len(failures), failures)

    return {
        "total":       total,
        "success":     success,
        "failed":      len(failures),
        "failures":    failures,
        "export_path": str(export_root)
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_output_path(folder: Path, filename: str) -> Path:
    """
    Resolve a non-conflicting output path inside a folder.

    If a file with the same name already exists, appends
    a numeric suffix to avoid overwriting.

    Args:
        folder:   The destination folder.
        filename: The desired filename.

    Returns:
        A Path that does not conflict with existing files.
    """
    output = folder / filename
    if not output.exists():
        return output

    stem      = Path(filename).stem
    suffix    = Path(filename).suffix
    counter   = 1

    while True:
        candidate = folder / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _sanitize_folder_name(name: str) -> str:
    """
    Remove characters that are invalid in folder names.

    Args:
        name: The proposed folder name.

    Returns:
        A sanitized folder name string.
    """
    invalid = '<>:"/\\|?*'
    for char in invalid:
        name = name.replace(char, "_")
    return name.strip() or "Unnamed"


def _write_export_summary(
    export_root: Path,
    total: int,
    success: int,
    failed: int,
    failures: list[str]
) -> None:
    """
    Write a plain text export summary file.

    Args:
        export_root: The root export folder.
        total:       Total documents attempted.
        success:     Successfully exported count.
        failed:      Failed count.
        failures:    List of failed document names.
    """
    now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines   = [
        "Personal Document Vault — Export Summary",
        f"Exported: {now}",
        f"",
        f"Total Documents:  {total}",
        f"Exported:         {success}",
        f"Failed:           {failed}",
    ]

    if failures:
        lines.append("")
        lines.append("Failed Documents:")
        for name in failures:
            lines.append(f"  - {name}")

    summary_path = export_root / "export_summary.txt"
    summary_path.write_text("\n".join(lines), encoding="utf-8")

