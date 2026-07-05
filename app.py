"""
app.py

Secure Vault Platform — Entry Point.

Initializes VaultCore, registers modules,
handles platform-wide authentication,
and launches the platform home screen.
"""

import tkinter as tk
import subprocess
import sys
from pathlib import Path

from vaultcore.config import PLATFORM_NAME, PLATFORM_VERSION, DEFAULT_GEOMETRY, MIN_WIDTH, MIN_HEIGHT
from vaultcore.logger import log_info, log_event, log_error
from vaultcore.module_manager import ModuleManager, ModuleDefinition
from vaultcore.notifications import NotificationService
from vaultcore.theme import Theme
from vaultcore.database import initialize_database
from ui.home import PlatformHome
from ui.about import AboutScreen


class SecureVaultPlatform:
    """
    Root platform controller.

    Initializes VaultCore services, registers all modules,
    and manages top-level navigation.
    """

    def __init__(self) -> None:
        """Initialize the platform window and all core services."""
        log_info(f"Starting {PLATFORM_NAME} v{PLATFORM_VERSION}")

        self._root = tk.Tk()
        self._root.title(PLATFORM_NAME)
        self._root.geometry(DEFAULT_GEOMETRY)
        self._root.minsize(MIN_WIDTH, MIN_HEIGHT)
        Theme.apply_to_root(self._root)

        # Initialize shared services
        initialize_database()
        self._notifications  = NotificationService(self._root)
        self._module_manager = ModuleManager()

        # Register all modules
        self._register_modules()

        # Show home screen
        self._show_home()

        log_event("PlatformReady", PLATFORM_NAME)

    def _register_modules(self) -> None:
        """Register all platform modules."""

        # Module 1 — Personal Document Vault
        self._module_manager.register(ModuleDefinition(
            id          = "document_vault",
            name        = "Document Vault",
            description = "Securely store, organize, and manage\npersonal documents offline.",
            icon        = "📄",
            version     = "1.0.0",
            available   = True,
            launcher    = self._launch_document_vault
        ))

        # Module 2 — Password Vault (Coming Soon)
        self._module_manager.register(ModuleDefinition(
            id          = "password_vault",
            name        = "Password Vault",
            description = "Encrypted password manager\nwith secure generation.",
            icon        = "🔒",
            version     = "0.0.0",
            available   = False,
            launcher    = None
        ))

        # Module 3 — Secure Archive (Coming Soon)
        self._module_manager.register(ModuleDefinition(
            id          = "secure_archive",
            name        = "Secure Archive",
            description = "Encrypted file archive\nwith compression support.",
            icon        = "📦",
            version     = "0.0.0",
            available   = False,
            launcher    = None
        ))

        # Module 4 — Secure Notes (Coming Soon)
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
        Launch the Document Vault module.

        Runs the existing PersonalDocumentVault application
        as a subprocess so it operates independently.
        """
        pdv_path = Path(
            r"C:\Users\ragha\Documents\Temp_Workspace\PersonalDocumentVault\app.py"
        )

        if not pdv_path.exists():
            log_error(f"Document Vault not found at: {pdv_path}")
            self._notifications.error("Document Vault not found.")
            return

        try:
            log_event("ModuleLaunched", "Document Vault")
            subprocess.Popen(
                [sys.executable, str(pdv_path)],
                cwd=str(pdv_path.parent)
            )
            self._notifications.success("Document Vault opened.")
        except Exception as error:
            log_error(f"Failed to launch Document Vault: {error}")
            self._notifications.error("Failed to open Document Vault.")

    def _clear_screen(self) -> None:
        """Remove all widgets from the window."""
        for widget in self._root.winfo_children():
            widget.destroy()

    def _show_home(self) -> None:
        """Display the platform home screen."""
        self._clear_screen()
        PlatformHome(
            parent         = self._root,
            module_manager = self._module_manager,
            on_settings    = self._show_settings,
            on_about       = self._show_about,
            on_exit        = self._root.quit
        )

    def _show_about(self) -> None:
        """Display the about screen."""
        self._clear_screen()
        AboutScreen(
            parent   = self._root,
            on_close = self._show_home
        )

    def _show_settings(self) -> None:
        """Display platform settings. Placeholder for Sprint 8."""
        self._notifications.info("Platform settings coming in Sprint 8.")

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self._root.mainloop()


def main() -> None:
    """Create and launch the Secure Vault Platform."""
    platform = SecureVaultPlatform()
    platform.run()


if __name__ == "__main__":
    main()
