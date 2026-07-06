"""
vaultcore/module_contract.py

Base Module Contract for the Secure Vault Platform.

Every module must implement this interface.
VaultCore uses this contract to manage module lifecycle,
query metadata, and check module health.

Document Vault is the reference implementation.
Password Vault, Secure Archive, and Secure Notes
must implement the same interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ModuleMetadata:
    """
    Runtime metadata provided by a module to the platform.

    Updated by the module during operation.
    Consumed by the platform dashboard for display.
    """
    module_id:       str
    name:            str
    version:         str
    status:          str            = "idle"
    health:          str            = "unknown"
    last_opened:     Optional[str]  = None
    last_backup:     Optional[str]  = None
    document_count:  int            = 0
    category_count:  int            = 0
    storage_used:    int            = 0
    extra:           dict           = field(default_factory=dict)

    def formatted_storage(self) -> str:
        """Return storage used as a human-readable string."""
        size = self.storage_used
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 ** 2):.1f} MB"


class VaultModule(ABC):
    """
    Abstract base class for all Secure Vault Platform modules.

    Every module must implement this interface.
    VaultCore uses this contract to manage the module lifecycle.

    Subclasses must implement all abstract methods.
    """

    @property
    @abstractmethod
    def module_id(self) -> str:
        """Return the unique module identifier."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the module display name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the module version string."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a short module description."""
        ...

    @property
    @abstractmethod
    def icon(self) -> str:
        """Return the module icon character."""
        ...

    @abstractmethod
    def initialize(self, master_password: str) -> bool:
        """
        Initialize the module with the platform session password.

        Called by the Module Manager before launching.

        Args:
            master_password: The authenticated master password.

        Returns:
            True if initialization succeeded.
        """
        ...

    @abstractmethod
    def launch(self) -> None:
        """
        Launch the module UI or process.

        Called after successful initialization.
        """
        ...

    @abstractmethod
    def lock(self) -> None:
        """
        Lock the module.

        Called when the platform session is locked.
        """
        ...

    @abstractmethod
    def unlock(self, master_password: str) -> bool:
        """
        Unlock the module.

        Called when the platform session is unlocked.

        Args:
            master_password: The re-authenticated master password.

        Returns:
            True if unlock succeeded.
        """
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """
        Gracefully shut down the module.

        Called when the platform is closing.
        Release all resources.
        """
        ...

    @abstractmethod
    def metadata(self) -> ModuleMetadata:
        """
        Return current module metadata for dashboard display.

        Called by the platform dashboard to populate module cards.

        Returns:
            A populated ModuleMetadata object.
        """
        ...

    @abstractmethod
    def health(self) -> str:
        """
        Return the current health status of the module.

        Returns:
            One of: 'healthy', 'warning', 'error', 'unknown'
        """
        ...
