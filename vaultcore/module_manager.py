"""
vaultcore/module_manager.py

Module registry and lifecycle manager for the Secure Vault Platform.
Updated in Sprint 9 to support VaultModule contract,
dynamic metadata, and lifecycle management.
"""

from dataclasses import dataclass
from typing import Optional, Callable, Dict
from vaultcore.logger import log_event, log_info, log_error
from vaultcore.module_contract import VaultModule, ModuleMetadata


@dataclass
class ModuleDefinition:
    """
    Describes a registered platform module.

    Attributes:
        id:           Unique module identifier.
        name:         Display name shown in the platform home.
        description:  Short description of the module.
        icon:         Emoji icon character for display.
        version:      Module version string.
        available:    True if the module is installed and available.
        launcher:     Callable that launches the module.
        vault_module: Optional VaultModule contract implementation.
    """
    id:           str
    name:         str
    description:  str
    icon:         str
    version:      str
    available:    bool
    launcher:     Optional[Callable]     = None
    vault_module: Optional[VaultModule]  = None


class ModuleManager:
    """
    Manages all registered platform modules.

    Supports both legacy launcher-based modules
    and new VaultModule contract implementations.
    """

    def __init__(self) -> None:
        """Initialize with an empty module registry."""
        self._modules: Dict[str, ModuleDefinition] = {}

    def register(self, module: ModuleDefinition) -> None:
        """
        Register a module with the platform.

        Args:
            module: The ModuleDefinition to register.
        """
        self._modules[module.id] = module
        log_event("ModuleRegistered", f"{module.name} v{module.version}")

    def get_all(self) -> list[ModuleDefinition]:
        """Return all registered modules."""
        return list(self._modules.values())

    def get(self, module_id: str) -> Optional[ModuleDefinition]:
        """Return a specific module by ID."""
        return self._modules.get(module_id)

    def launch(self, module_id: str) -> bool:
        """
        Launch a module by its ID.

        Prefers VaultModule contract launch over legacy launcher.

        Args:
            module_id: The unique module identifier.

        Returns:
            True if the module launched successfully.
        """
        module = self._modules.get(module_id)

        if module is None:
            log_error(f"Module not found: {module_id}")
            return False

        if not module.available:
            log_info(f"Module not available: {module.name}")
            return False

        try:
            if module.vault_module is not None:
                module.vault_module.launch()
                return True
            elif module.launcher is not None:
                log_event("ModuleLaunching", module.name)
                module.launcher()
                return True
            return False
        except Exception as error:
            log_error(f"Module launch failed: {module.name} - {error}")
            return False

    def initialize_module(
        self,
        module_id: str,
        master_password: str
    ) -> bool:
        """
        Initialize a VaultModule contract module.

        Args:
            module_id:       The module to initialize.
            master_password: The session master password.

        Returns:
            True if initialization succeeded.
        """
        module = self._modules.get(module_id)

        if module is None or module.vault_module is None:
            return False

        return module.vault_module.initialize(master_password)

    def get_metadata(self, module_id: str) -> Optional[ModuleMetadata]:
        """
        Return live metadata for a module.

        Args:
            module_id: The module to query.

        Returns:
            A ModuleMetadata object or None.
        """
        module = self._modules.get(module_id)

        if module is None or module.vault_module is None:
            return None

        return module.vault_module.metadata()

    def get_all_metadata(self) -> Dict[str, ModuleMetadata]:
        """
        Return metadata for all modules that implement VaultModule.

        Returns:
            A dict mapping module_id to ModuleMetadata.
        """
        result = {}
        for module_id, module in self._modules.items():
            if module.vault_module is not None:
                try:
                    result[module_id] = module.vault_module.metadata()
                except Exception:
                    pass
        return result

    def shutdown_all(self) -> None:
        """Shut down all active VaultModule instances."""
        for module in self._modules.values():
            if module.vault_module is not None:
                try:
                    module.vault_module.shutdown()
                except Exception as error:
                    log_error(f"Shutdown error for {module.name}: {error}")
        log_info("All modules shut down.")

    def lock_all(self) -> None:
        """Lock all active VaultModule instances."""
        for module in self._modules.values():
            if module.vault_module is not None:
                try:
                    module.vault_module.lock()
                except Exception:
                    pass

    def unlock_all(self, master_password: str) -> None:
        """
        Unlock all active VaultModule instances.

        Args:
            master_password: The re-authenticated master password.
        """
        for module in self._modules.values():
            if module.vault_module is not None:
                try:
                    module.vault_module.unlock(master_password)
                except Exception:
                    pass
