"""
app.py

Secure Vault Platform — Entry Point.

Sprint 8: Platform authentication, session management,
activity monitoring, auto-lock, security center,
and shared settings integrated.
"""

import tkinter as tk
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

from vaultcore.config import PLATFORM_NAME, PLATFORM_VERSION, DEFAULT_GEOMETRY, MIN_WIDTH, MIN_HEIGHT
from vaultcore.logger import log_info, log_event, log_error
from vaultcore.module_manager import ModuleManager, ModuleDefinition
from vaultcore.notifications import NotificationService
from vaultcore.theme import Theme
from vaultcore.database import initialize_database
from vaultcore.session import SessionManager
from vaultcore.activity_monitor import ActivityMonitor
from vaultcore.settings_service import SettingsService
from vaultcore.backup import create_backup, BACKUP_FOLDER

from ui.login import PlatformLoginScreen
from ui.home import PlatformHome
from ui.about import AboutScreen
from ui.security_center import SecurityCenter
from ui.platform_settings import PlatformSettingsScreen


class SecureVaultPlatform:
    """
    Root platform controller.

    Manages the full platform lifecycle including
    initialization, authentication, session management,
    activity monitoring, module launching, and shutdown.
    """

    def __init__(self) -> None:
        """Initialize all platform services and show login."""
        log_info(f"Starting {PLATFORM_NAME} v{PLATFORM_VERSION}")

        self._root = tk.Tk()
        self._root.title(PLATFORM_NAME)
        self._root.geometry(DEFAULT_GEOMETRY)
        self._root.minsize(MIN_WIDTH, MIN_HEIGHT)
        Theme.apply_to_root(self._root)

        # Initialize shared services
        initialize_database()

        self._session_manager  = SessionManager()
        self._settings_service = SettingsService()
        self._notifications    = NotificationService(self._root)
        self._module_manager   = ModuleManager()

        # Activity monitor with lock callback
        self._activity_monitor = ActivityMonitor(
            root            = self._root,
            session_manager = self._session_manager,
            on_lock         = self._handle_auto_lock
        )

        # Apply saved auto-lock setting
        seconds = self._settings_service.get_auto_lock_seconds()
        self._activity_monitor.set_idle_timeout(seconds)

        # Register modules
        self._register_modules()

        # Handle auto-backup check
        self._check_auto_backup()

        # Show platform login
        self._show_login()

        # Safe shutdown on window close
        self._root.protocol("WM_DELETE_WINDOW", self._handle_exit)

        log_event("PlatformReady", PLATFORM_NAME)

    def _register_modules(self) -> None:
        """Register all platform modules."""
        self._module_manager.register(ModuleDefinition(
            id          = "document_vault",
            name        = "Document Vault",
            description = "Securely store, organize, and manage\npersonal documents offline.",
            icon        = "📄",
            version     = "1.0.0",
            available   = True,
            launcher    = self._launch_document_vault
        ))

        self._module_manager.register(ModuleDefinition(
            id          = "password_vault",
            name        = "Password Vault",
            description = "Encrypted password manager\nwith secure generation.",
            icon        = "🔒",
            version     = "0.0.0",
            available   = False,
            launcher    = None
        ))

        self._module_manager.register(ModuleDefinition(
            id          = "secure_archive",
            name        = "Secure Archive",
            description = "Encrypted file archive\nwith compression support.",
            icon        = "📦",
            version     = "0.0.0",
            available   = False,
            launcher    = None
        ))

        self._module_manager.register(ModuleDefinition(
            id          = "secure_notes",
            name        = "Secure Notes",
            description = "Private encrypted notes\nwith rich text support.",
            icon        = "📝",
            version     = "0.0.0",
            available   = False,
            launcher    = None
        ))

        log_info(f"Registered {len(self._module_manager.get_all())} modules")

    def _launch_document_vault(self) -> None:
        """
        Launch the Document Vault module as a subprocess.

        The session master password is passed as an environment
        variable so Document Vault can skip its own login screen.
        """
        pdv_path = Path(
            r"C:\Users\ragha\Documents\Temp_Workspace\PersonalDocumentVault\app.py"
        )

        if not pdv_path.exists():
            log_error(f"Document Vault not found: {pdv_path}")
            self._notifications.error("Document Vault not found.")
            return

        if not self._session_manager.is_authenticated():
            self._notifications.error("Platform not authenticated.")
            return

        try:
            import os
            env = os.environ.copy()
            env["SVP_MASTER_PASSWORD"] = self._session_manager.get_master_password()
            env["SVP_AUTHENTICATED"]   = "1"

            log_event("ModuleLaunching", "Document Vault")
            subprocess.Popen(
                [sys.executable, str(pdv_path)],
                cwd = str(pdv_path.parent),
                env = env
            )
            self._notifications.success("Document Vault opened.")
            log_event("ModuleLaunched", "Document Vault")

        except Exception as error:
            log_error(f"Failed to launch Document Vault: {error}")
            self._notifications.error("Failed to open Document Vault.")

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
        """Lock the platform and return to login."""
        self._session_manager.lock()
        self._activity_monitor.stop()
        log_event("PlatformLocked", "User initiated")
        self._notifications.info("Platform locked.")
        self._show_login()

    def _handle_auto_lock(self) -> None:
        """Handle auto-lock triggered by idle timeout."""
        log_event("AutoLockTriggered", "Idle timeout")
        self._show_login()

    def _handle_exit(self) -> None:
        """
        Safely shut down the platform.

        Destroys session, clears sensitive data,
        writes final log entries, and exits.
        """
        log_event("PlatformShutdown", "User initiated exit")
        self._activity_monitor.stop()
        self._session_manager.destroy_session()
        log_info("Session destroyed. Platform exiting.")
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
                            "last_backup_date", datetime.now().isoformat()
                        )
                        log_event("AutoBackup", "Backup created successfully")

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
