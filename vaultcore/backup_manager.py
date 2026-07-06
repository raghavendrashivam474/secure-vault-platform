"""
vaultcore/backup_manager.py

Shared Backup Manager for the Secure Vault Platform.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from vaultcore.backup import (
    create_backup, restore_backup, verify_backup,
    list_backups, get_latest_backup_date,
    get_backup_count, BACKUP_FOLDER
)
from vaultcore.event_bus import platform_bus, Events
from vaultcore.logger import log_event, log_error, log_info


class BackupManager:
    """Centralized backup management for the Secure Vault Platform."""

    def __init__(self) -> None:
        self._backup_folder: Path = BACKUP_FOLDER

    def create(
        self,
        master_password: str,
        destination: Optional[Path] = None
    ) -> tuple[bool, str]:
        """Create an encrypted vault backup."""
        folder = destination or self._backup_folder
        success, message = create_backup(master_password, folder)
        if success:
            log_event("BackupCreated", message)
            platform_bus.publish(Events.BACKUP_CREATED, {
                "path": message,
                "time": datetime.now().isoformat()
            })
        else:
            log_error(f"Backup failed: {message}")
            platform_bus.publish(Events.BACKUP_FAILED, {"reason": message})
        return success, message

    def restore(
        self,
        backup_path: Path,
        backup_password: str
    ) -> tuple[bool, str]:
        """Restore a vault from a backup archive."""
        success, message = restore_backup(backup_path, backup_password)
        if success:
            log_event("BackupRestored", str(backup_path))
        else:
            log_error(f"Restore failed: {message}")
        return success, message

    def verify(self, backup_path: Path, password: str) -> tuple[bool, str]:
        """Verify the integrity of a backup archive."""
        return verify_backup(backup_path, password)

    def list_all(self) -> list[Path]:
        """Return all available backup files."""
        return list_backups(self._backup_folder)

    def get_latest_date(self) -> Optional[str]:
        """Return date of most recent backup."""
        return get_latest_backup_date()

    def get_count(self) -> int:
        """Return total number of backup files."""
        return get_backup_count()

    def is_backup_due(self, frequency: str, last_backup_str: str) -> bool:
        """Determine whether a backup is due."""
        if frequency == "Never":
            return False
        if not last_backup_str:
            return True
        try:
            last  = datetime.fromisoformat(last_backup_str)
            delta = datetime.now() - last
            if frequency == "Daily"   and delta >= timedelta(days=1):
                return True
            if frequency == "Weekly"  and delta >= timedelta(weeks=1):
                return True
            if frequency == "Monthly" and delta >= timedelta(days=30):
                return True
            return False
        except ValueError:
            return True

    def set_backup_folder(self, folder: Path) -> None:
        """Set the backup destination folder."""
        self._backup_folder = folder
        folder.mkdir(parents=True, exist_ok=True)
        log_info(f"Backup folder set to: {folder}")
