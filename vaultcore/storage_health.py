"""
vaultcore/storage_health.py

Storage Health Service for the Secure Vault Platform.
"""

from pathlib import Path
from vaultcore.vault_filesystem import VaultFilesystem
from vaultcore.storage_index import (
    get_total_indexed_size,
    get_module_storage_size,
    get_file_count
)
from vaultcore.backup import get_backup_count, get_latest_backup_date


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.1f} GB"


class StorageHealthService:
    """Monitors platform storage health and usage."""

    def __init__(self, filesystem: VaultFilesystem) -> None:
        self._fs = filesystem

    def get_full_report(self) -> dict:
        """Generate a complete storage health report."""
        vault_size   = self._fs.get_total_size()

        # Also include Personal Document Vault standalone storage
        from pathlib import Path
        pdv_encrypted = Path(r"C:\Users\ragha\Documents\Temp_Workspace\PersonalDocumentVault\vault\encrypted")
        if pdv_encrypted.exists():
            for f in pdv_encrypted.rglob("*"):
                if f.is_file():
                    try:
                        vault_size += f.stat().st_size
                    except Exception:
                        pass
        indexed_size = get_total_indexed_size()
        backup_size  = self._get_dir_size(self._fs.backups_dir)
        cache_size   = self._get_dir_size(self._fs.cache_dir)
        temp_size    = self._get_dir_size(self._fs.temp_dir)
        log_size     = self._get_dir_size(self._fs.logs_dir)
        file_count   = get_file_count()
        backup_count = get_backup_count()
        latest_backup = get_latest_backup_date() or "Never"
        doc_vault_size = get_module_storage_size("document_vault")

        return {
            "vault_size":        vault_size,
            "vault_size_fmt":    _format_size(vault_size),
            "indexed_size":      indexed_size,
            "indexed_size_fmt":  _format_size(indexed_size),
            "backup_size":       backup_size,
            "backup_size_fmt":   _format_size(backup_size),
            "cache_size":        cache_size,
            "cache_size_fmt":    _format_size(cache_size),
            "temp_size":         temp_size,
            "temp_size_fmt":     _format_size(temp_size),
            "log_size":          log_size,
            "log_size_fmt":      _format_size(log_size),
            "total_files":       file_count,
            "backup_count":      backup_count,
            "latest_backup":     latest_backup,
            "doc_vault_size":    _format_size(doc_vault_size),
            "health_status":     self._assess_health(vault_size, backup_count)
        }

    def _assess_health(self, vault_size: int, backup_count: int) -> str:
        if backup_count == 0:
            return "warning"
        if vault_size > 500 * 1024 * 1024:
            return "warning"
        return "healthy"

    def _get_dir_size(self, directory: Path) -> int:
        if not directory.exists():
            return 0
        total = 0
        for f in directory.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except Exception:
                    pass
        return total

