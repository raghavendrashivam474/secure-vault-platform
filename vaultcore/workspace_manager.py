"""
vaultcore/workspace_manager.py

Temporary Workspace Manager for the Secure Vault Platform.
"""

import uuid
import shutil
from pathlib import Path

from vaultcore.vault_filesystem import VaultFilesystem
from vaultcore.logger import log_event, log_error, log_debug


class WorkspaceManager:
    """Manages temporary workspaces for platform modules."""

    def __init__(self, filesystem: VaultFilesystem) -> None:
        self._fs         = filesystem
        self._workspaces: dict[str, Path] = {}

    def allocate(self, module_id: str, label: str = "") -> Path:
        """Allocate a new temporary workspace for a module."""
        workspace_id = str(uuid.uuid4())[:8]
        name         = f"{label}_{workspace_id}" if label else workspace_id
        workspace    = self._fs.module_temp_dir(module_id) / name
        try:
            workspace.mkdir(parents=True, exist_ok=True)
            self._workspaces[workspace_id] = workspace
            return workspace
        except Exception as error:
            log_error(f"[Workspace] Allocation failed: {error}")
            return self._fs.module_temp_dir(module_id)

    def release(self, workspace: Path) -> None:
        """Release and delete a temporary workspace."""
        try:
            if workspace.exists():
                shutil.rmtree(workspace)
            self._workspaces = {
                k: v for k, v in self._workspaces.items()
                if v != workspace
            }
        except Exception as error:
            log_error(f"[Workspace] Release failed: {error}")

    def cleanup_module(self, module_id: str) -> None:
        """Clean up all temporary workspaces for a module."""
        temp_dir = self._fs.module_temp_dir(module_id)
        try:
            if temp_dir.exists():
                for item in temp_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            log_event("WorkspaceCleanup", module_id)
        except Exception as error:
            log_error(f"[Workspace] Cleanup failed: {error}")

    def cleanup_all(self) -> None:
        """Clean up all tracked temporary workspaces."""
        for workspace in list(self._workspaces.values()):
            self.release(workspace)
        log_event("WorkspaceCleanupAll", "Platform shutdown")

    def get_active_count(self) -> int:
        """Return number of active workspaces."""
        return len(self._workspaces)
