"""
app.py

Secure Vault Platform - Entry Point.
Sprint 9: Native module integration, Event Bus, VaultModule contract.
"""

import tkinter as tk
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

from vaultcore.config import (
    PLATFORM_NAME, PLATFORM_VERSION,
    DEFAULT_GEOMETRY, MIN_WIDTH, MIN_HEIGHT
)
from vaultcore.logger import log_info, log_event, log_error
from vaultcore.module_manager import ModuleManager, ModuleDefinition
from vaultcore.notifications import NotificationService
from vaultcore.theme import Theme
from vaultcore.database import initialize_database
from vaultcore.session import SessionManager
from vaultcore.activity_monitor import ActivityMonitor
from vaultcore.settings_service import SettingsService
from vaultcore.backup import create_backup, BACKUP_FOLDER
from vaultcore.event_bus import platform_bus, Events

from modules.document_vault.module import DocumentVaultModule

from ui.login import PlatformLoginScreen
from ui.home import PlatformHome
from ui.about import AboutScreen
from ui.security_center import SecurityCenter
from ui.platform_settings import PlatformSettingsScreen


class SecureVaultPlatform:
    """Root platform controller."""

    def __init__(self) -> None:
        """Initialize all platform services."""
        log_info(f"Starting {PLATFORM_NAME} v{PLATFORM_VERSION}")

        self._root = tk.Tk()
        self._root.title(PLATFORM_NAME)
        self._root.geometry(DEFAULT_GEOMETRY)
        self._root.minsize(MIN_WIDTH, MIN_HEIGHT)
        Theme.apply_to_root(self._root)

        initialize_database()

        self._session_manager  = SessionManager()
        self._settings_service = SettingsService()
        self._notifications    = NotificationService(self._root)
        self._module_manager   = ModuleManager()

        self._activity_monitor = ActivityMonitor(
            root            = self._root,
            session_manager = self._session_manager,
            on_lock         = self._handle_auto_lock
        )

        seconds = self._settings_service.get_auto_lock_seconds()
        self._activity_monitor.set_idle_timeout(seconds)

        self._setup_event_listeners()
        self._register_modules()
        self._check_auto_backup()
        self._show_login()

        self._root.protocol("WM_DELETE_WINDOW", self._handle_exit)
        log_event("PlatformReady", PLATFORM_NAME)

    def _setup_event_listeners(self) -> None:
        """Register platform-level Event Bus listeners."""

        def on_module_started(event: str, data: dict) -> None:
            name = data.get("name", "Module")
            self._notifications.success(f"{name} opened.")

        def on_module_closed(event: str, data: dict) -> None:
            module_id = data.get("module_id", "")
            log_event("EventBus", f"Module closed: {module_id}")

        def on_document_imported(event: str, data: dict) -> None:
            name = data.get("name", "Document")
            self._notifications.success(f"Imported: {name}")

        def on_backup_created(event: str, data: dict) -> None:
            self._notifications.success("Backup created successfully.")

        def on_export_complete(event: str, data: dict) -> None:
            count = data.get("count", 0)
            self._notifications.success(f"Export complete: {count} file(s).")

        platform_bus.subscribe(Events.MODULE_STARTED,    on_module_started)
        platform_bus.subscribe(Events.MODULE_CLOSED,     on_module_closed)
        platform_bus.subscribe(Events.DOCUMENT_IMPORTED, on_document_imported)
        platform_bus.subscribe(Events.BACKUP_CREATED,    on_backup_created)
        platform_bus.subscribe(Events.DOCUMENT_EXPORTED, on_export_complete)

        log_info("Event Bus listeners registered.")

    def _register_modules(self) -> None:
        """Register all platform modules."""
        self._doc_vault_module = DocumentVaultModule()

        self._module_manager.register(ModuleDefinition(
            id           = "document_vault",
            name         = "Document Vault",
            description  = "Securely store, organize, and manage\npersonal documents offline.",
            icon         = "📄",
            version      = "1.0.0",
            available    = True,
            launcher     = self._launch_document_vault,
            vault_module = self._doc_vault_module
        ))

        self._module_manager.register(ModuleDefinition(
            id          = "password_vault",
            name        = "Password Vault",
            description = "Encrypted password manager\nwith secure generation.",
            icon        = "🔒",
            version     = "0.0.0",
            available   = False
        ))

        self._module_manager.register(ModuleDefinition(
            id          = "secure_archive",
            name        = "Secure Archive",
            description = "Encrypted file archive\nwith compression support.",
            icon        = "📦",
            version     = "0.0.0",
            available   = False
        ))

        self._module_manager.register(ModuleDefinition(
            id          = "secure_notes",
            name        = "Secure Notes",
            description = "Private encrypted notes\nwith rich text support.",
            icon        = "📝",
            version     = "0.0.0",
            available   = False
        ))

        log_info(f"Registered {len(self._module_manager.get_all())} modules")

    def _launch_document_vault(self) -> None:
        """Initialize and launch Document Vault."""
        if not self._session_manager.is_authenticated():
            self._notifications.error("Platform not authenticated.")
            return

        password = self._session_manager.get_master_password()

        if not password:
            self._notifications.error("No active session password.")
            return

        # Initialize directly on the stored module instance
        self._doc_vault_module._master_password = password
        self._doc_vault_module._initialized     = True

        log_event("ModuleInitializing", "Document Vault")
        self._doc_vault_module.launch()

    def _clear_screen(self) -> None:
        """Remove all widgets from the window."""
        for widget in self._root.winfo_children():
            widget.destroy()

    def _show_login(self) -> None:
        """Display the platform login screen."""
        self._clear_screen()
        PlatformLoginScreen(
            parent           = self._root,
            session_manager  = self._session_manager,
            on_authenticated = self._on_authenticated
        )

    def _on_authenticated(self) -> None:
        """Handle successful platform authentication."""
        log_event("Authenticated", "Platform session active")
        self._notifications.success("Platform unlocked.")
        self._show_dashboard()

    def _show_dashboard(self) -> None:
        """Display the authenticated platform dashboard."""
        self._clear_screen()
        PlatformHome(
            parent          = self._root,
            module_manager  = self._module_manager,
            session_manager = self._session_manager,
            on_settings     = self._show_settings,
            on_security     = self._show_security_center,
            on_about        = self._show_about,
            on_lock         = self._handle_lock,
            on_exit         = self._handle_exit
        )

    def _show_settings(self) -> None:
        """Display the platform settings screen."""
        self._clear_screen()
        PlatformSettingsScreen(
            parent           = self._root,
            settings_service = self._settings_service,
            activity_monitor = self._activity_monitor,
            on_close         = self._show_dashboard
        )

    def _show_security_center(self) -> None:
        """Display the security center."""
        self._clear_screen()
        SecurityCenter(
            parent           = self._root,
            session_manager  = self._session_manager,
            settings_service = self._settings_service,
            on_close         = self._show_dashboard
        )

    def _show_about(self) -> None:
        """Display the about screen."""
        self._clear_screen()
        AboutScreen(
            parent   = self._root,
            on_close = self._show_dashboard
        )

    def _handle_lock(self) -> None:
        """Lock the platform and all modules."""
        self._module_manager.lock_all()
        self._session_manager.lock()
        self._activity_monitor.stop()
        log_event("PlatformLocked", "User initiated")
        self._notifications.info("Platform locked.")
        self._show_login()

    def _handle_auto_lock(self) -> None:
        """Handle auto-lock triggered by idle timeout."""
        self._module_manager.lock_all()
        log_event("AutoLockTriggered", "Idle timeout")
        self._show_login()

    def _handle_exit(self) -> None:
        """Safely shut down the platform."""
        log_event("PlatformShutdown", "User initiated exit")
        self._activity_monitor.stop()
        self._module_manager.shutdown_all()
        self._session_manager.destroy_session()
        log_info("Platform shutdown complete.")
        self._root.quit()

    def _check_auto_backup(self) -> None:
        """Check whether an automatic backup is due."""
        frequency = self._settings_service.get("backup_frequency")
        if frequency == "Never":
            return

        last_str = self._settings_service.get("last_backup_date")
        if not last_str:
            return

        try:
            last  = datetime.fromisoformat(last_str)
            now   = datetime.now()
            delta = now - last
            due   = False

            if frequency == "Daily"   and delta >= timedelta(days=1):
                due = True
            elif frequency == "Weekly"  and delta >= timedelta(weeks=1):
                due = True
            elif frequency == "Monthly" and delta >= timedelta(days=30):
                due = True

            if due:
                password = self._session_manager.get_master_password()
                if password:
                    success, message = create_backup(password, BACKUP_FOLDER)
                    if success:
                        self._settings_service.set(
                            "last_backup_date",
                            datetime.now().isoformat()
                        )
                        platform_bus.publish(Events.BACKUP_CREATED, {
                            "path": message
                        })
                        log_event("AutoBackup", "Backup created")
        except Exception as error:
            log_error(f"Auto-backup check failed: {error}")

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self._root.mainloop()


def main() -> None:
    """Create and launch the Secure Vault Platform."""
    platform = SecureVaultPlatform()
    platform.run()


if __name__ == "__main__":
    main()
