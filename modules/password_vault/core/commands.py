"""
modules/password_vault/core/commands.py

Password Vault command definitions.

Registers module actions with the VaultCore Command Registry.
Commands are the standardized way to invoke domain operations.
"""

from typing import Callable
from vaultcore.command_registry import CommandRegistry, Command


# Command constants
PWV_CREATE          = "password.create"
PWV_SEARCH          = "password.search"
PWV_GENERATE        = "password.generate"
PWV_AUDIT           = "password.audit"
PWV_IMPORT          = "password.import"
PWV_EXPORT          = "password.export"
PWV_RESTORE         = "password.restore"
PWV_SHOW_FAVORITES  = "password.show_favorites"
PWV_SHOW_WEAK       = "password.show_weak"
PWV_SHOW_AGING      = "password.show_aging"


def register_password_commands(
    registry: CommandRegistry,
    handlers: dict[str, Callable]
) -> None:
    """
    Register all Password Vault commands with the registry.

    Args:
        registry: The VaultCore CommandRegistry.
        handlers: Dict mapping command ID to handler callable.
    """
    commands = [
        (PWV_CREATE,         "Create Password",   "Add a new password entry"),
        (PWV_SEARCH,         "Search Passwords",  "Search vault by metadata"),
        (PWV_GENERATE,       "Generate Password", "Open password generator"),
        (PWV_AUDIT,          "Run Security Audit","Analyze vault for issues"),
        (PWV_IMPORT,         "Import CSV",        "Import passwords from CSV"),
        (PWV_EXPORT,         "Export Vault",      "Encrypted vault export"),
        (PWV_RESTORE,        "Restore Vault",     "Restore from encrypted export"),
        (PWV_SHOW_FAVORITES, "Show Favorites",    "View favorite passwords"),
        (PWV_SHOW_WEAK,      "Show Weak",         "View weak passwords"),
        (PWV_SHOW_AGING,     "Show Aging",        "View aging passwords"),
    ]

    for command_id, name, description in commands:
        if command_id in handlers:
            registry.register(Command(
                command_id  = command_id,
                name        = name,
                description = description,
                handler     = handlers[command_id],
                module_id   = "password_vault"
            ))


def unregister_password_commands(registry: CommandRegistry) -> None:
    """
    Remove all Password Vault commands from the registry.

    Args:
        registry: The VaultCore CommandRegistry.
    """
    commands = [
        PWV_CREATE, PWV_SEARCH, PWV_GENERATE, PWV_AUDIT,
        PWV_IMPORT, PWV_EXPORT, PWV_RESTORE,
        PWV_SHOW_FAVORITES, PWV_SHOW_WEAK, PWV_SHOW_AGING,
    ]
    for cmd_id in commands:
        registry.unregister(cmd_id)
