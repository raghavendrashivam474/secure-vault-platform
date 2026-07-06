"""
modules/document_vault/module.py

Document Vault Module Contract Implementation.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from vaultcore.module_contract import VaultModule, ModuleMetadata
from vaultcore.event_bus import platform_bus, Events
from vaultcore.logger import log_event, log_info, log_error
from vaultcore.database import get_vault_statistics
from vaultcore.backup import get_latest_backup_date, get_vault_size


PDV_PATH: Path = Path(
    r"C:\Users\ragha\Documents\Temp_Workspace\PersonalDocumentVault\app.py"
)


class DocumentVaultModule(VaultModule):
    """
    Document Vault module implementing the VaultModule contract.
    """

    def __init__(self) -> None:
        """Initialize the module."""
        self._master_password: str                      = ""
        self._initialized:     bool                     = False
        self._process:         Optional[subprocess.Popen] = None
        self._launch_time:     Optional[str]            = None

    @property
    def module_id(self) -> str:
        return "document_vault"

    @property
    def name(self) -> str:
        return "Document Vault"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Securely store, organize, and manage\npersonal documents offline."

    @property
    def icon(self) -> str:
        return "📄"

    def initialize(self, master_password: str) -> bool:
        """Initialize with the platform session password."""
        self._master_password = master_password
        self._initialized     = True
        log_event("ModuleInitialized", self.name)
        return True

    def launch(self) -> None:
        """Launch Document Vault as a subprocess."""
        if not PDV_PATH.exists():
            log_error(f"[DocumentVault] PDV not found at: {PDV_PATH}")
            return

        try:
            env = os.environ.copy()
            env["SVP_PLATFORM"]         = "1"
            env["SVP_AUTHENTICATED"]    = "1"
            env["SVP_MODULE_ID"]        = self.module_id
            env["SVP_PLATFORM_VERSION"] = "0.2.0"
            env["SVP_MASTER_PASSWORD"]  = self._master_password

            self._process = subprocess.Popen(
                [sys.executable, str(PDV_PATH)],
                cwd = str(PDV_PATH.parent),
                env = env
            )
            self._launch_time = datetime.now(timezone.utc).isoformat()

            log_event("ModuleLaunched", self.name)
            platform_bus.publish(Events.MODULE_STARTED, {
                "module_id": self.module_id,
                "name":      self.name,
                "pid":       self._process.pid
            })

        except Exception as error:
            log_error(f"[DocumentVault] Launch failed: {error}")

    def lock(self) -> None:
        """Lock the module."""
        log_event("ModuleLocked", self.name)
        platform_bus.publish(Events.MODULE_LOCKED, {
            "module_id": self.module_id
        })

    def unlock(self, master_password: str) -> bool:
        """Unlock the module."""
        if master_password:
            self._master_password = master_password
            log_event("ModuleUnlocked", self.name)
            return True
        return False

    def shutdown(self) -> None:
        """Gracefully shut down the module."""
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except Exception:
                pass

        self._master_password = ""
        self._initialized     = False

        log_event("ModuleClosed", self.name)
        platform_bus.publish(Events.MODULE_CLOSED, {
            "module_id": self.module_id
        })

    def metadata(self) -> ModuleMetadata:
        """Return current module metadata."""
        try:
            # Read from Personal Document Vault database
            import sqlite3
            from pathlib import Path
            pdv_db = Path(r"C:\Users\ragha\Documents\Temp_Workspace\PersonalDocumentVault\database\vault.db")

            doc_count = 0
            cat_count = 0
            integrity_issues = 0
            expired_count = 0

            if pdv_db.exists():
                con = sqlite3.connect(pdv_db)
                cur = con.cursor()
                try:
                    cur.execute("SELECT COUNT(*) FROM documents")
                    doc_count = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM categories")
                    cat_count = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM documents WHERE integrity_status = 0")
                    integrity_issues = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM documents WHERE expiry_date IS NOT NULL AND expiry_date < date('now')")
                    expired_count = cur.fetchone()[0]
                except Exception:
                    pass
                con.close()

            # Storage from PDV database (only tracked documents)
            storage_used = 0
            if pdv_db.exists():
                con = sqlite3.connect(pdv_db)
                cur = con.cursor()
                try:
                    cur.execute("SELECT SUM(file_size) FROM documents")
                    result = cur.fetchone()[0]
                    storage_used = result if result else 0
                except Exception:
                    pass
                con.close()

            stats = {
                "document_count": doc_count,
                "category_count": cat_count,
                "integrity_issues": integrity_issues,
                "expired_count": expired_count
            }
            last_backup  = get_latest_backup_date() or "Never"

            return ModuleMetadata(
                module_id      = self.module_id,
                name           = self.name,
                version        = self.version,
                status         = "running" if self._is_running() else "idle",
                health         = self.health(),
                last_opened    = self._launch_time,
                last_backup    = last_backup,
                document_count = stats.get("document_count", 0),
                category_count = stats.get("category_count", 0),
                storage_used   = storage_used
            )
        except Exception:
            return ModuleMetadata(
                module_id = self.module_id,
                name      = self.name,
                version   = self.version,
                status    = "idle",
                health    = "unknown"
            )

    def health(self) -> str:
        """Return current health status."""
        try:
            stats = get_vault_statistics()
            if stats.get("integrity_issues", 0) > 0:
                return "warning"
            if stats.get("expired_count", 0) > 0:
                return "warning"
            return "healthy"
        except Exception:
            return "unknown"

    def _is_running(self) -> bool:
        """Return True if the subprocess is running."""
        if self._process is None:
            return False
        return self._process.poll() is None


