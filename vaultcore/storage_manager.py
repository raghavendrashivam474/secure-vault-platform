"""
vaultcore/storage_manager.py

Central Storage Manager for the Secure Vault Platform.
"""

import shutil
from pathlib import Path
from typing import Optional

from vaultcore.vault_filesystem import VaultFilesystem
from vaultcore.event_bus import platform_bus, Events
from vaultcore.logger import log_event, log_error, log_debug


class StorageManager:
    """Centralized filesystem authority for the platform."""

    def __init__(self, filesystem: VaultFilesystem) -> None:
        self._fs = filesystem

    def resolve(self, module_id: str, relative_path: str) -> Path:
        return self._fs.module_dir(module_id) / relative_path

    def get_encrypted_dir(self, module_id: str) -> Path:
        return self._fs.module_encrypted_dir(module_id)

    def get_export_dir(self, module_id: str) -> Path:
        return self._fs.module_export_dir(module_id)

    def get_cache_dir(self, module_id: str) -> Path:
        return self._fs.module_cache_dir(module_id)

    def get_temp_dir(self, module_id: str) -> Path:
        return self._fs.module_temp_dir(module_id)

    def exists(self, path: Path) -> bool:
        return path.exists()

    def read_bytes(self, path: Path) -> Optional[bytes]:
        try:
            return path.read_bytes()
        except Exception as error:
            log_error(f"[Storage] Read failed: {path} - {error}")
            return None

    def write_bytes(self, path: Path, data: bytes) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return True
        except Exception as error:
            log_error(f"[Storage] Write failed: {path} - {error}")
            return False

    def delete(self, path: Path) -> bool:
        try:
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as error:
            log_error(f"[Storage] Delete failed: {path} - {error}")
            return False

    def copy(self, source: Path, destination: Path) -> bool:
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            return True
        except Exception as error:
            log_error(f"[Storage] Copy failed: {source} - {error}")
            return False

    def move(self, source: Path, destination: Path) -> bool:
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            return True
        except Exception as error:
            log_error(f"[Storage] Move failed: {source} - {error}")
            return False

    def list_files(self, directory: Path, pattern: str = "*") -> list[Path]:
        if not directory.exists():
            return []
        return sorted(directory.glob(pattern))

    def create_directory(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as error:
            log_error(f"[Storage] Directory creation failed: {path} - {error}")
            return False

    def get_size(self, path: Path) -> int:
        try:
            if path.is_file():
                return path.stat().st_size
            elif path.is_dir():
                return sum(
                    f.stat().st_size for f in path.rglob("*") if f.is_file()
                )
            return 0
        except Exception:
            return 0

    def provision_module(self, module_id: str) -> None:
        self._fs.provision_module(module_id)
        log_event("StorageProvisioned", module_id)
