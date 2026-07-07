"""
vaultcore/platform_actions.py

Global Platform Actions for the Secure Vault Platform.

Provides centralized action definitions and registration
for the platform's built-in operations.
"""

from typing import Callable
from vaultcore.command_registry import CommandRegistry, Command


class PlatformActions:
    """
    Standard platform command constants.
    """

    LOCK_PLATFORM      = "platform.lock"
    EXIT_PLATFORM      = "platform.exit"
    OPEN_SETTINGS      = "platform.settings"
    OPEN_SECURITY      = "platform.security"
    OPEN_STORAGE       = "platform.storage"
    OPEN_ACTIVITY      = "platform.activity"
    OPEN_NOTIFICATIONS = "platform.notifications"
    OPEN_ABOUT         = "platform.about"
    BACKUP_ALL         = "platform.backup_all"


def register_platform_actions(
    registry: CommandRegistry,
    handlers: dict[str, Callable]
) -> None:
    """
    Register all standard platform commands.

    Args:
        registry: The CommandRegistry to register with.
        handlers: A dict mapping action IDs to handler callables.
    """
    actions = [
        (PlatformActions.LOCK_PLATFORM,      "Lock Platform",       "Lock and require re-authentication"),
        (PlatformActions.EXIT_PLATFORM,      "Exit Platform",       "Shut down the platform"),
        (PlatformActions.OPEN_SETTINGS,      "Open Settings",       "Access platform preferences"),
        (PlatformActions.OPEN_SECURITY,      "Open Security",       "View security center"),
        (PlatformActions.OPEN_STORAGE,       "Storage Dashboard",   "View storage health"),
        (PlatformActions.OPEN_ACTIVITY,      "Recent Activity",     "View activity feed"),
        (PlatformActions.OPEN_NOTIFICATIONS, "Notifications",       "View notification center"),
        (PlatformActions.OPEN_ABOUT,         "About Platform",      "View platform information"),
        (PlatformActions.BACKUP_ALL,         "Backup All Modules",  "Create full platform backup"),
    ]

    for action_id, name, description in actions:
        if action_id in handlers:
            registry.register(Command(
                command_id  = action_id,
                name        = name,
                description = description,
                handler     = handlers[action_id],
                module_id   = "platform"
            ))
