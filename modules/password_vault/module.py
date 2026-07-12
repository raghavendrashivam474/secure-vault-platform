"""
modules/password_vault/module.py

Password Vault Module - Native VaultCore module implementation.
"""

import tkinter as tk
from datetime import datetime, timezone
from typing import Optional

from vaultcore.module_contract import VaultModule, ModuleMetadata
from vaultcore.event_bus import platform_bus, Events
from vaultcore.logger import log_event, log_info, log_error

from modules.password_vault.core.database import (
    initialize_password_database,
    get_password_statistics
)
from modules.password_vault.core.search_adapter import password_search_handler
from vaultcore.search_framework import SearchAdapter


class PasswordVaultModule(VaultModule):
    """
    Password Vault - Native VaultCore module.
    """

    def __init__(self) -> None:
        self._master_password: str  = ""
        self._initialized:     bool = False
        self._window:          Optional[tk.Toplevel] = None
        self._launch_time:     Optional[str] = None

        self._clipboard           = None
        self._dialogs             = None
        self._notifications       = None
        self._notification_center = None
        self._activity_service    = None
        self._recent_items        = None
        self._storage_manager     = None
        self._parent_root         = None
        self._search_framework    = None

    @property
    def module_id(self) -> str:
        return "password_vault"

    @property
    def name(self) -> str:
        return "Password Vault"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Encrypted password manager\nwith secure generation."

    @property
    def icon(self) -> str:
        return "🔒"

    def inject_services(
        self,
        parent_root,
        clipboard,
        dialogs,
        notifications,
        notification_center,
        activity_service,
        recent_items,
        storage_manager,
        search_framework=None
    ) -> None:
        """Inject platform services from VaultCore."""
        self._parent_root         = parent_root
        self._search_framework    = search_framework
        self._clipboard           = clipboard
        self._dialogs             = dialogs
        self._notifications       = notifications
        self._notification_center = notification_center
        self._activity_service    = activity_service
        self._recent_items        = recent_items
        self._storage_manager     = storage_manager

    def initialize(self, master_password: str) -> bool:
        """Initialize the module."""
        self._master_password = master_password
        self._initialized     = True
        initialize_password_database()

        # Register search adapter with VaultCore Search Framework
        if self._search_framework:
            self._search_framework.register_adapter(SearchAdapter(
                module_id = self.module_id,
                handler   = password_search_handler
            ))
            log_info("[PasswordVault] Search adapter registered.")

        log_event("PasswordVaultInitialized")
        return True

    def launch(self) -> None:
        """Launch the Password Vault UI."""
        if not self._master_password:
            log_error("[PasswordVault] No master password available.")
            return

        # Auto-initialize if needed
        if not self._initialized:
            initialize_password_database()
            self._initialized = True

        if self._window and self._window.winfo_exists():
            self._window.lift()
            self._window.focus_force()
            return

        try:
            from modules.password_vault.ui.dashboard import PasswordVaultDashboard

            self._window = tk.Toplevel(self._parent_root)
            self._window.title("Password Vault")
            self._window.geometry("1100x700")
            self._window.minsize(900, 550)
            self._window.configure(bg="#1a1a2e")

            PasswordVaultDashboard(
                parent              = self._window,
                master_password     = self._master_password,
                clipboard           = self._clipboard,
                dialogs             = self._dialogs,
                notifications       = self._notifications,
                notification_center = self._notification_center,
                activity_service    = self._activity_service,
                recent_items        = self._recent_items,
                on_close            = self._handle_close
            )

            self._launch_time = datetime.now(timezone.utc).isoformat()
            self._window.protocol("WM_DELETE_WINDOW", self._handle_close)

            log_event("PasswordVaultLaunched")
            platform_bus.publish(Events.MODULE_STARTED, {
                "module_id": self.module_id,
                "name":      self.name
            })

        except Exception as error:
            log_error(f"[PasswordVault] Launch failed: {error}")
            import traceback
            traceback.print_exc()

    def _handle_close(self) -> None:
        """Handle window close."""
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None

        platform_bus.publish(Events.MODULE_CLOSED, {
            "module_id": self.module_id
        })

    def lock(self) -> None:
        """Lock the module."""
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None
        log_event("PasswordVaultLocked")

    def unlock(self, master_password: str) -> bool:
        """Unlock the module."""
        if master_password:
            self._master_password = master_password
            return True
        return False

    def shutdown(self) -> None:
        """Shut down the module."""
        self.lock()
        self._master_password = ""
        self._initialized     = False
        log_event("PasswordVaultShutdown")

    def metadata(self) -> ModuleMetadata:
        """Return live module metadata."""
        try:
            stats = get_password_statistics()
            return ModuleMetadata(
                module_id      = self.module_id,
                name           = self.name,
                version        = self.version,
                status         = "running" if self._window else "idle",
                health         = self.health(),
                last_opened    = self._launch_time,
                document_count = stats["total_passwords"],
                category_count = stats["categories"],
                storage_used   = 0
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
            stats = get_password_statistics()
            if stats["weak_passwords"] > 0:
                return "warning"
            return "healthy"
        except Exception:
            return "unknown"

