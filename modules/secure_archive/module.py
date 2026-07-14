"""
modules/secure_archive/module.py

Secure Archive - Native VaultCore module.

Implements the VaultModule contract.
Zero infrastructure code — all platform services injected.
"""

import tkinter as tk
from datetime import datetime, timezone
from typing import Optional

from vaultcore.module_contract import VaultModule, ModuleMetadata
from vaultcore.event_bus import platform_bus, Events
from vaultcore.logger import log_event, log_info, log_error


class SecureArchiveModule(VaultModule):
    """
    Secure Archive - Intelligent project archiving module.

    Sprint 14 delivers the archive creation and restoration pipeline
    without final encryption. Encryption envelope arrives in a future sprint.
    """

    def __init__(self) -> None:
        self._master_password: str  = ""
        self._initialized:     bool = False
        self._window:          Optional[tk.Toplevel] = None
        self._launch_time:     Optional[str] = None

        # Injected VaultCore services
        self._clipboard           = None
        self._dialogs             = None
        self._notifications       = None
        self._notification_center = None
        self._activity_service    = None
        self._recent_items        = None
        self._storage_manager     = None
        self._search_framework    = None
        self._command_registry    = None
        self._parent_root         = None

    # ── VaultModule contract properties ───────────────────────────────────────

    @property
    def module_id(self) -> str:
        return "secure_archive"

    @property
    def name(self) -> str:
        return "Secure Archive"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return "Intelligent project archiving\nwith verified restoration."

    @property
    def icon(self) -> str:
        return "📦"

    # ── Service injection ─────────────────────────────────────────────────────

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
        search_framework=None,
        command_registry=None
    ) -> None:
        """Inject platform services from VaultCore."""
        self._parent_root         = parent_root
        self._clipboard           = clipboard
        self._dialogs             = dialogs
        self._notifications       = notifications
        self._notification_center = notification_center
        self._activity_service    = activity_service
        self._recent_items        = recent_items
        self._storage_manager     = storage_manager
        self._search_framework    = search_framework
        self._command_registry    = command_registry

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self, master_password: str) -> bool:
        """Initialize the module with the platform session password."""
        self._master_password = master_password
        self._initialized     = True
        log_event("SecureArchiveInitialized")
        return True

    def launch(self) -> None:
        """Launch the Secure Archive UI as a Toplevel window."""
        if self._window and self._window.winfo_exists():
            self._window.lift()
            self._window.focus_force()
            return

        try:
            from modules.secure_archive.ui.dashboard import SecureArchiveDashboard

            self._window = tk.Toplevel(self._parent_root)
            self._window.title("Secure Archive")
            self._window.geometry("1100x700")
            self._window.minsize(900, 550)
            self._window.configure(bg="#1a1a2e")

            SecureArchiveDashboard(
                parent              = self._window,
                master_password     = self._master_password,
                clipboard           = self._clipboard,
                dialogs             = self._dialogs,
                notifications       = self._notifications,
                notification_center = self._notification_center,
                activity_service    = self._activity_service,
                recent_items        = self._recent_items,
                storage_manager     = self._storage_manager,
                on_close            = self._handle_close
            )

            self._launch_time = datetime.now(timezone.utc).isoformat()
            self._window.protocol("WM_DELETE_WINDOW", self._handle_close)

            log_event("SecureArchiveLaunched")
            platform_bus.publish(Events.MODULE_STARTED, {
                "module_id": self.module_id,
                "name":      self.name
            })

        except Exception as error:
            log_error(f"[SecureArchive] Launch failed: {error}")
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
        log_event("SecureArchiveLocked")

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
        log_event("SecureArchiveShutdown")

    def metadata(self) -> ModuleMetadata:
        """Return module metadata for dashboard display."""
        return ModuleMetadata(
            module_id      = self.module_id,
            name           = self.name,
            version        = self.version,
            status         = "running" if self._window else "idle",
            health         = "healthy",
            last_opened    = self._launch_time,
            document_count = 0,
            category_count = 0,
            storage_used   = 0
        )

    def health(self) -> str:
        """Return current health status."""
        return "healthy"
