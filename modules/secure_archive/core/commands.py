"""
modules/secure_archive/core/commands.py

Secure Archive command definitions.
Registers module actions with the VaultCore Command Registry.
"""

from typing import Callable
from vaultcore.command_registry import CommandRegistry, Command


# Command constants
ARC_CREATE      = "archive.create"
ARC_ANALYZE     = "archive.analyze"
ARC_RESTORE     = "archive.restore"
ARC_SHOW_RECENT = "archive.show_recent"


def register_archive_commands(
    registry: CommandRegistry,
    handlers: dict[str, Callable]
) -> None:
    """Register all Secure Archive commands."""
    commands = [
        (ARC_CREATE,      "Create Archive",  "Scan and archive a project"),
        (ARC_ANALYZE,     "Analyze Project", "Preview archive plan without creating"),
        (ARC_RESTORE,     "Restore Archive", "Restore an archive package"),
        (ARC_SHOW_RECENT, "Recent Archives", "View recent archive activity"),
    ]

    for command_id, name, description in commands:
        if command_id in handlers:
            registry.register(Command(
                command_id  = command_id,
                name        = name,
                description = description,
                handler     = handlers[command_id],
                module_id   = "secure_archive"
            ))
