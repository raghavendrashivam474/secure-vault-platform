"""
core/metadata.py

Metadata extraction for the Personal Document Vault.
Extracts file information and returns structured metadata objects.
"""

from pathlib import Path
from datetime import datetime, timezone

from modules.document_vault.models.document import Document
from vaultcore.file_utils import get_mime_type, generate_encrypted_filename


def extract_metadata(file_path: Path) -> Document:
    """
    Extract metadata from a file and return a Document object.

    This function reads basic filesystem metadata only.
    No file content is read or modified at this stage.

    Args:
        file_path: The path to the file being imported.

    Returns:
        A Document object populated with extracted metadata.
        The id field is None until the record is saved to the database.

    Raises:
        FileNotFoundError: If the file does not exist.
        OSError: If file metadata cannot be read.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    stat            = file_path.stat()
    file_extension  = file_path.suffix.lower().lstrip(".")
    mime_type       = get_mime_type(file_path)
    encrypted_name  = generate_encrypted_filename()

    last_modified = datetime.fromtimestamp(
        stat.st_mtime,
        tz=timezone.utc
    ).isoformat()

    date_added = datetime.now(timezone.utc).isoformat()

    return Document(
        id             = None,
        uuid           = encrypted_name.replace(".enc", ""),
        original_name  = file_path.name,
        encrypted_name = encrypted_name,
        file_type      = file_extension,
        mime_type      = mime_type,
        file_size      = stat.st_size,
        date_added     = date_added,
        last_modified  = last_modified,
        notes          = None,
        category_id    = None
    )

