"""
vaultcore/module_manager.py

Module registry and loader for the Secure Vault Platform.
Manages discovery, registration, and launching of modules.
"""

from dataclasses import dataclass
from typing import Optional, Callable
from vaultcore.logger import log_event, log_info, log_error


@dataclass
class ModuleDefinition:
    """
    Describes a registered platform module.

    Attributes:
        id:           Unique module identifier.
        name:         Display name shown in the platform home.
        description:  Short description of the module.
        icon:         Emoji or icon character for display.
        version:      Module version string.
        available:    True if the module is installed and available.
        launcher:     Callable that launches the module.
                      None if the module is not yet available.
    """
    id:          str
    name:        str
    description: str
    icon:        str
    version:     str
    available:   bool
    launcher:    Optional[Callable] = None


class ModuleManager:
    """
    Manages all registered platform modules.

    Modules register themselves with the platform at startup.
    The platform home screen reads from the ModuleManager
    to display available and upcoming modules.
    """

    def __init__(self) -> None:
        """Initialize with an empty module registry."""
        self._modules: dict[str, ModuleDefinition] = {}

    def register(self, module: ModuleDefinition) -> None:
        """
        Register a module with the platform.

        Args:
            module: The ModuleDefinition to register.
        """
        self._modules[module.id] = module
        log_event("ModuleRegistered", f"{module.name} v{module.version}")

    def get_all(self) -> list[ModuleDefinition]:
        """
        Return all registered modules in registration order.

        Returns:
            A list of ModuleDefinition objects.
        """
        return list(self._modules.values())

    def get(self, module_id: str) -> Optional[ModuleDefinition]:
        """
        Return a specific module by ID.

        Args:
            module_id: The unique module identifier.

        Returns:
            A ModuleDefinition or None if not found.
        """
        return self._modules.get(module_id)

    def launch(self, module_id: str) -> bool:
        """
        Launch a module by its ID.

        Args:
            module_id: The unique module identifier.

        Returns:
            True if the module launched successfully.
            False if the module is unavailable or not found.
        """
        module = self._modules.get(module_id)

        if module is None:
            log_error(f"Module not found: {module_id}")
            return False

        if not module.available or module.launcher is None:
            log_info(f"Module not available: {module.name}")
            return False

        try:
            log_event("ModuleLaunching", module.name)
            module.launcher()
            return True
        except Exception as error:
            log_error(f"Module launch failed: {module.name} — {error}")
            return False

