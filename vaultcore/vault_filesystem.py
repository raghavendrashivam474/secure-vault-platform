"""
vaultcore/vault_filesystem.py

Standardized Vault Filesystem for the Secure Vault Platform.
"""

from pathlib import Path

VAULT_ROOT: Path = Path(".")


class VaultFilesystem:
    """Manages the canonical storage layout for the platform."""

    def __init__(self, root: Path = VAULT_ROOT) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    @property
    def database_dir(self) -> Path:
        return self._root / "database"

    @property
    def backups_dir(self) -> Path:
        return self._root / "backups"

    @property
    def logs_dir(self) -> Path:
        return self._root / "logs"

    @property
    def exports_dir(self) -> Path:
        return self._root / "exports"

    @property
    def cache_dir(self) -> Path:
        return self._root / "cache"

    @property
    def temp_dir(self) -> Path:
        return self._root / "temp"

    @property
    def assets_dir(self) -> Path:
        return self._root / "assets"

    def module_dir(self, module_id: str) -> Path:
        return self._root / "vault" / module_id

    def module_encrypted_dir(self, module_id: str) -> Path:
        return self.module_dir(module_id) / "encrypted"

    def module_cache_dir(self, module_id: str) -> Path:
        return self.module_dir(module_id) / "cache"

    def module_export_dir(self, module_id: str) -> Path:
        return self.module_dir(module_id) / "exports"

    def module_temp_dir(self, module_id: str) -> Path:
        return self.module_dir(module_id) / "temp"

    def provision_module(self, module_id: str) -> None:
        """Create all required directories for a module."""
        for directory in [
            self.module_dir(module_id),
            self.module_encrypted_dir(module_id),
            self.module_cache_dir(module_id),
            self.module_export_dir(module_id),
            self.module_temp_dir(module_id),
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def provision_platform(self) -> None:
        """Create all required platform-level directories."""
        for directory in [
            self.database_dir,
            self.backups_dir,
            self.logs_dir,
            self.exports_dir,
            self.cache_dir,
            self.temp_dir,
            self.assets_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def get_total_size(self) -> int:
        """Calculate total size of all vault contents in bytes."""
        total     = 0
        vault_dir = self._root / "vault"
        if vault_dir.exists():
            for f in vault_dir.rglob("*"):
                if f.is_file():
                    try:
                        total += f.stat().st_size
                    except Exception:
                        pass
        return total
