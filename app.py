"""
app.py

Secure Vault Platform - Entry Point.
Sprint 11: Complete Platform Services Layer integrated.
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
from vaultcore.event_bus import platform_bus, Events

# Storage infrastructure (Sprint 10)
from vaultcore.vault_filesystem import VaultFilesystem
from vaultcore.storage_manager import StorageManager
from vaultcore.workspace_manager import WorkspaceManager
from vaultcore.storage_index import initialize_storage_index
from vaultcore.metadata_service import MetadataService
from vaultcore.backup_manager import BackupManager
from vaultcore.storage_health import StorageHealthService

# Platform Services Layer (Sprint 11)
from vaultcore.clipboard_manager import ClipboardManager
from vaultcore.dialog_framework import DialogFramework
from vaultcore.notification_center import NotificationCenter
from vaultcore.recent_activity import RecentActivityService
from vaultcore.recent_items import RecentItemsService
from vaultcore.command_registry import CommandRegistry
from vaultcore.permission_manager import PermissionManager
from vaultcore.import_export import ImportExportFramework
from vaultcore.search_framework import SearchFramework
from vaultcore.platform_actions import PlatformActions, register_platform_actions

from modules.document_vault.module import DocumentVaultModule
from modules.password_vault.module import PasswordVaultModule

from ui.login import PlatformLoginScreen
from ui.home import PlatformHome
from ui.about import AboutScreen
from ui.security_center import SecurityCenter
from ui.platform_settings import PlatformSettingsScreen
from ui.storage_dashboard import StorageDashboard
from ui.notification_panel import NotificationPanel
from ui.activity_panel import ActivityPanel


class SecureVaultPlatform:
    """Root platform controller with complete four-layer architecture."""

    def __init__(self) -> None:
        """Initialize all platform services."""
        log_info(f"Starting {PLATFORM_NAME} v{PLATFORM_VERSION}")

        self._root = tk.Tk()
        self._root.title(PLATFORM_NAME)
        self._root.geometry(DEFAULT_GEOMETRY)
        self._root.minsize(MIN_WIDTH, MIN_HEIGHT)
        Theme.apply_to_root(self._root)

        # Core initialization
        initialize_database()
        initialize_storage_index()

        # Initialize password vault database
        from modules.password_vault.core.database import initialize_password_database
        initialize_password_database()

        # Security Layer
        self._session_manager  = SessionManager()

        # Application Layer
        self._module_manager   = ModuleManager()
        self._settings_service = SettingsService()
        self._notifications    = NotificationService(self._root)

        # Data Layer
        self._filesystem        = VaultFilesystem()
        self._storage_manager   = StorageManager(self._filesystem)
        self._workspace_manager = WorkspaceManager(self._filesystem)
        self._metadata_service  = MetadataService()
        self._backup_manager    = BackupManager()
        self._health_service    = StorageHealthService(self._filesystem)

        # Platform Services Layer (Sprint 11)
        self._clipboard         = ClipboardManager(self._root)
        self._dialogs           = DialogFramework(self._root)
        self._notif_center      = NotificationCenter()
        self._activity_service  = RecentActivityService()
        self._recent_items      = RecentItemsService()
        self._command_registry  = CommandRegistry()
        self._permissions       = PermissionManager()
        self._import_export     = ImportExportFramework()
        self._search_framework  = SearchFramework()

        self._permissions.set_confirm_handler(self._dialogs.confirm_destructive)

        # Provision platform directories
        self._filesystem.provision_platform()

        # Activity monitor
        self._activity_monitor = ActivityMonitor(
            root            = self._root,
            session_manager = self._session_manager,
            on_lock         = self._handle_auto_lock
        )

        seconds = self._settings_service.get_auto_lock_seconds()
        self._activity_monitor.set_idle_timeout(seconds)

        self._setup_event_listeners()
        self._register_modules()
        self._register_platform_commands()
        self._check_auto_backup()
        self._show_login()

        self._root.protocol("WM_DELETE_WINDOW", self._handle_exit)
        log_event("PlatformReady", PLATFORM_NAME)

    def _setup_event_listeners(self) -> None:
        """Wire Event Bus listeners to Notification Center and Activity."""

        def on_module_started(event: str, data: dict) -> None:
            name = data.get("name", "Module")
            self._notifications.success(f"{name} opened.")
            self._notif_center.add("Module Opened", f"{name} launched.", "success", data.get("module_id", "platform"))
            self._activity_service.record("ModuleOpened", data.get("module_id", "platform"), name)

        def on_module_closed(event: str, data: dict) -> None:
            module_id = data.get("module_id", "")
            self._workspace_manager.cleanup_module(module_id)
            self._activity_service.record("ModuleClosed", module_id)

        def on_document_imported(event: str, data: dict) -> None:
            name = data.get("name", "Document")
            self._notif_center.add("Document Imported", f"Imported: {name}", "success", data.get("module_id", "platform"))
            self._activity_service.record("DocumentImported", data.get("module_id", "platform"), name)

        def on_backup_created(event: str, data: dict) -> None:
            self._notifications.success("Backup created successfully.")
            self._notif_center.add("Backup Created", "Encrypted backup created.", "success")
            self._activity_service.record("BackupCreated", "platform", data.get("path", ""))

        def on_export_complete(event: str, data: dict) -> None:
            count = data.get("count", 0)
            self._notif_center.add("Export Complete", f"{count} file(s) exported.", "success", data.get("module_id", "platform"))
            self._activity_service.record("ExportComplete", data.get("module_id", "platform"), f"{count} files")

        platform_bus.subscribe(Events.MODULE_STARTED,    on_module_started)
        platform_bus.subscribe(Events.MODULE_CLOSED,     on_module_closed)
        platform_bus.subscribe(Events.DOCUMENT_IMPORTED, on_document_imported)
        platform_bus.subscribe(Events.BACKUP_CREATED,    on_backup_created)
        platform_bus.subscribe(Events.DOCUMENT_EXPORTED, on_export_complete)

        log_info("Event Bus listeners registered.")

    def _register_modules(self) -> None:
        """Register and provision all platform modules."""
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

        # Register Password Vault as native module
        self._password_vault_module = PasswordVaultModule()
        self._password_vault_module.inject_services(
            parent_root         = self._root,
            clipboard           = self._clipboard,
            dialogs             = self._dialogs,
            notifications       = self._notifications,
            notification_center = self._notif_center,
            activity_service    = self._activity_service,
            recent_items        = self._recent_items,
            storage_manager     = self._storage_manager
        )

        self._module_manager.register(ModuleDefinition(
            id           = "password_vault",
            name         = "Password Vault",
            description  = "Encrypted password manager\nwith secure generation.",
            icon         = "🔒",
            version      = "1.0.0",
            available    = True,
            launcher     = self._launch_password_vault,
            vault_module = self._password_vault_module
        ))

        for definition in [
            ("secure_archive", "Secure Archive",  "Encrypted file archive\nwith compression support.",   "📦"),
            ("secure_notes",   "Secure Notes",    "Private encrypted notes\nwith rich text support.",    "📝"),
        ]:
            module_id, name, desc, icon = definition
            self._module_manager.register(ModuleDefinition(
                id          = module_id,
                name        = name,
                description = desc,
                icon        = icon,
                version     = "0.0.0",
                available   = False
            ))

        self._storage_manager.provision_module("document_vault")
        self._storage_manager.provision_module("password_vault")
        log_info(f"Registered {len(self._module_manager.get_all())} modules")

    def _register_platform_commands(self) -> None:
        """Register standard platform commands."""
        handlers = {
            PlatformActions.LOCK_PLATFORM:      self._handle_lock,
            PlatformActions.EXIT_PLATFORM:      self._handle_exit,
            PlatformActions.OPEN_SETTINGS:      self._show_settings,
            PlatformActions.OPEN_SECURITY:      self._show_security_center,
            PlatformActions.OPEN_STORAGE:       self._show_storage_dashboard,
            PlatformActions.OPEN_ACTIVITY:      self._show_activity_panel,
            PlatformActions.OPEN_NOTIFICATIONS: self._show_notification_panel,
            PlatformActions.OPEN_ABOUT:         self._show_about,
        }
        register_platform_actions(self._command_registry, handlers)
        log_info(f"Registered {self._command_registry.count()} platform commands")

    def _launch_document_vault(self) -> None:
        """Initialize and launch Document Vault."""
        if not self._session_manager.is_authenticated():
            self._notifications.error("Platform not authenticated.")
            return

        password = self._session_manager.get_master_password()
        if not password:
            self._notifications.error("No active session password.")
            return

        self._doc_vault_module._master_password = password
        self._doc_vault_module._initialized     = True

        log_event("ModuleInitializing", "Document Vault")
        self._doc_vault_module.launch()

    def _launch_password_vault(self) -> None:
        """Initialize and launch Password Vault."""
        if not self._session_manager.is_authenticated():
            self._notifications.error("Platform not authenticated.")
            return
        password = self._session_manager.get_master_password()
        if not password:
            return
        self._password_vault_module.initialize(password)
        self._password_vault_module.launch()

    def _clear_screen(self) -> None:
        for widget in self._root.winfo_children():
            widget.destroy()

    def _show_login(self) -> None:
        self._clear_screen()
        PlatformLoginScreen(
            parent           = self._root,
            session_manager  = self._session_manager,
            on_authenticated = self._on_authenticated
        )

    def _on_authenticated(self) -> None:
        log_event("Authenticated", "Platform session active")
        # Set session password on Password Vault
        password = self._session_manager.get_master_password()
        if hasattr(self, "_password_vault_module") and password:
            self._password_vault_module._master_password = password
            self._password_vault_module._initialized     = True
        self._notifications.success("Platform unlocked.")
        self._notif_center.add("Platform Unlocked", "Authentication successful.", "success")
        self._activity_service.record("PlatformUnlocked", "platform")
        self._show_dashboard()

    def _show_dashboard(self) -> None:
        self._clear_screen()
        PlatformHome(
            parent          = self._root,
            module_manager  = self._module_manager,
            session_manager = self._session_manager,
            on_settings     = self._show_settings,
            on_security     = self._show_security_center,
            on_about        = self._show_about,
            on_lock         = self._handle_lock,
            on_exit         = self._handle_exit,
            on_storage      = self._show_storage_dashboard,
            on_notifications = self._show_notification_panel,
            on_activity      = self._show_activity_panel
        )

    def _show_settings(self) -> None:
        self._clear_screen()
        PlatformSettingsScreen(
            parent           = self._root,
            settings_service = self._settings_service,
            activity_monitor = self._activity_monitor,
            on_close         = self._show_dashboard
        )

    def _show_security_center(self) -> None:
        self._clear_screen()
        SecurityCenter(
            parent           = self._root,
            session_manager  = self._session_manager,
            settings_service = self._settings_service,
            on_close         = self._show_dashboard
        )

    def _show_storage_dashboard(self) -> None:
        self._clear_screen()
        StorageDashboard(
            parent         = self._root,
            health_service = self._health_service,
            on_close       = self._show_dashboard
        )

    def _show_notification_panel(self) -> None:
        self._clear_screen()
        NotificationPanel(
            parent              = self._root,
            notification_center = self._notif_center,
            on_close            = self._show_dashboard
        )

    def _show_activity_panel(self) -> None:
        self._clear_screen()
        ActivityPanel(
            parent           = self._root,
            activity_service = self._activity_service,
            on_close         = self._show_dashboard
        )

    def _show_about(self) -> None:
        self._clear_screen()
        AboutScreen(
            parent   = self._root,
            on_close = self._show_dashboard
        )

    def _handle_lock(self) -> None:
        self._module_manager.lock_all()
        self._session_manager.lock()
        self._activity_monitor.stop()
        self._activity_service.record("PlatformLocked", "platform")
        log_event("PlatformLocked", "User initiated")
        self._notifications.info("Platform locked.")
        self._show_login()

    def _handle_auto_lock(self) -> None:
        self._module_manager.lock_all()
        self._activity_service.record("AutoLocked", "platform", "Idle timeout")
        log_event("AutoLockTriggered", "Idle timeout")
        self._show_login()

    def _handle_exit(self) -> None:
        log_event("PlatformShutdown", "User initiated exit")
        self._activity_service.record("PlatformShutdown", "platform")
        self._activity_monitor.stop()
        self._workspace_manager.cleanup_all()
        self._module_manager.shutdown_all()
        self._session_manager.destroy_session()
        log_info("Platform shutdown complete.")
        self._root.quit()

    def _check_auto_backup(self) -> None:
        frequency   = self._settings_service.get("backup_frequency")
        last_backup = self._settings_service.get("last_backup_date")

        if self._backup_manager.is_backup_due(frequency, last_backup):
            password = self._session_manager.get_master_password()
            if password:
                success, message = self._backup_manager.create(password)
                if success:
                    self._settings_service.set(
                        "last_backup_date",
                        datetime.now().isoformat()
                    )

    def run(self) -> None:
        self._root.mainloop()


def main() -> None:
    platform = SecureVaultPlatform()
    platform.run()


if __name__ == "__main__":
    main()




