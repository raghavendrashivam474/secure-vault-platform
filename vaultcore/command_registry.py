"""
vaultcore/command_registry.py

Command Registry for the Secure Vault Platform.

Standardizes user actions through registered commands.
UI elements trigger commands instead of directly calling logic.
Enables future keyboard shortcuts, macros, and audit trails.
"""

from typing import Callable, Optional
from dataclasses import dataclass, field

from vaultcore.logger import log_event, log_debug, log_error


@dataclass
class Command:
    """
    Represents a registered platform command.

    Attributes:
        command_id:  Unique identifier.
        name:        Display name.
        description: Short description.
        handler:     The callable to execute.
        module_id:   The registering module.
        shortcut:    Optional keyboard shortcut.
        requires_auth: True if authentication required.
    """
    command_id:    str
    name:          str
    description:   str
    handler:       Callable
    module_id:     str = "platform"
    shortcut:      Optional[str] = None
    requires_auth: bool = True


class CommandRegistry:
    """
    Centralized command registry.

    All platform actions should be registered as commands
    and executed through this registry.
    """

    def __init__(self) -> None:
        """Initialize with an empty registry."""
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        """
        Register a command with the platform.

        Args:
            command: The Command to register.
        """
        self._commands[command.command_id] = command
        log_debug(f"[CommandRegistry] Registered: {command.command_id}")

    def unregister(self, command_id: str) -> None:
        """
        Remove a command from the registry.

        Args:
            command_id: The command to remove.
        """
        if command_id in self._commands:
            del self._commands[command_id]

    def execute(self, command_id: str, *args, **kwargs) -> bool:
        """
        Execute a registered command.

        Args:
            command_id: The command to execute.
            *args:      Positional arguments passed to handler.
            **kwargs:   Keyword arguments passed to handler.

        Returns:
            True if execution succeeded.
        """
        command = self._commands.get(command_id)

        if command is None:
            log_error(f"[CommandRegistry] Unknown command: {command_id}")
            return False

        try:
            log_event("CommandExecuted", command_id)
            command.handler(*args, **kwargs)
            return True
        except Exception as error:
            log_error(f"[CommandRegistry] Failed {command_id}: {error}")
            return False

    def get(self, command_id: str) -> Optional[Command]:
        """Return a command by ID."""
        return self._commands.get(command_id)

    def get_all(self) -> list[Command]:
        """Return all registered commands."""
        return list(self._commands.values())

    def get_by_module(self, module_id: str) -> list[Command]:
        """Return commands registered by a specific module."""
        return [c for c in self._commands.values() if c.module_id == module_id]

    def count(self) -> int:
        """Return the total number of registered commands."""
        return len(self._commands)
