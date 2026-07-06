"""
vaultcore/metadata_service.py

Centralized Metadata Service for the Secure Vault Platform.
"""

from typing import Optional
from vaultcore.logger import log_event, log_error, log_debug


class MetadataService:
    """Centralized metadata management for all platform modules."""

    def get_vault_statistics(self) -> dict:
        """Return platform-wide vault statistics."""
        try:
            from vaultcore.database import get_vault_statistics
            return get_vault_statistics()
        except Exception as error:
            log_error(f"[Metadata] Statistics failed: {error}")
            return {}

    def get_document_count(self) -> int:
        """Return total number of documents stored."""
        return self.get_vault_statistics().get("document_count", 0)

    def get_category_count(self) -> int:
        """Return total number of categories."""
        return self.get_vault_statistics().get("category_count", 0)

    def get_setting(self, key: str, default: str = "") -> str:
        """Read a platform setting by key."""
        try:
            from vaultcore.database import load_setting
            return load_setting(key, default)
        except Exception as error:
            log_error(f"[Metadata] Setting read failed: {key}")
            return default

    def save_setting(self, key: str, value: str) -> None:
        """Save a platform setting."""
        try:
            from vaultcore.database import save_setting
            save_setting(key, value)
        except Exception as error:
            log_error(f"[Metadata] Setting save failed: {key}")

    def get_last_backup_date(self) -> Optional[str]:
        """Return date of most recent backup."""
        try:
            from vaultcore.backup import get_latest_backup_date
            return get_latest_backup_date()
        except Exception:
            return None

    def get_integrity_issues(self) -> int:
        """Return number of documents with integrity failures."""
        return self.get_vault_statistics().get("integrity_issues", 0)
