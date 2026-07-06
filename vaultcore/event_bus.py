"""
vaultcore/event_bus.py

Platform Event Bus for the Secure Vault Platform.

Provides loosely coupled communication between modules
and platform services. Modules publish events. VaultCore
distributes them to all registered listeners.

No module should communicate directly with another module.
All cross-module communication passes through the Event Bus.
"""

from typing import Callable, Any
from vaultcore.logger import log_event, log_debug


# Defined platform event names
class Events:
    """Standard platform event name constants."""

    PLATFORM_STARTED        = "platform.started"
    PLATFORM_LOCKED         = "platform.locked"
    PLATFORM_UNLOCKED       = "platform.unlocked"
    PLATFORM_SHUTDOWN       = "platform.shutdown"

    MODULE_STARTED          = "module.started"
    MODULE_CLOSED           = "module.closed"
    MODULE_LOCKED           = "module.locked"
    MODULE_UNLOCKED         = "module.unlocked"

    DOCUMENT_IMPORTED       = "document.imported"
    DOCUMENT_DELETED        = "document.deleted"
    DOCUMENT_UPDATED        = "document.updated"
    DOCUMENT_EXPORTED       = "document.exported"

    BACKUP_CREATED          = "backup.created"
    BACKUP_FAILED           = "backup.failed"

    INTEGRITY_SCAN_COMPLETE = "integrity.scan.complete"
    SEARCH_PERFORMED        = "search.performed"

    CATEGORY_CREATED        = "category.created"
    CATEGORY_DELETED        = "category.deleted"

    NOTIFICATION_REQUESTED  = "notification.requested"
    SETTINGS_CHANGED        = "settings.changed"


class EventBus:
    """
    Central event distribution system.

    Components register listeners for specific events.
    When an event is published, all registered listeners
    for that event are invoked in registration order.
    """

    def __init__(self) -> None:
        """Initialize with an empty listener registry."""
        self._listeners: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, listener: Callable) -> None:
        """
        Register a listener for a specific event.

        Args:
            event:    The event name string.
            listener: The callable to invoke when the event fires.
        """
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(listener)
        log_debug(f"EventBus: Subscribed to '{event}'")

    def unsubscribe(self, event: str, listener: Callable) -> None:
        """
        Remove a listener from an event.

        Args:
            event:    The event name string.
            listener: The callable to remove.
        """
        if event in self._listeners:
            self._listeners[event] = [
                l for l in self._listeners[event] if l != listener
            ]

    def publish(self, event: str, data: dict = None) -> None:
        """
        Publish an event to all registered listeners.

        Args:
            event: The event name string.
            data:  Optional dictionary of event data.
        """
        if data is None:
            data = {}

        log_debug(f"EventBus: Publishing '{event}' with {data}")

        listeners = self._listeners.get(event, [])
        for listener in listeners:
            try:
                listener(event, data)
            except Exception as error:
                log_debug(f"EventBus: Listener error for '{event}': {error}")

    def get_subscribed_events(self) -> list[str]:
        """
        Return a list of all events with active listeners.

        Returns:
            A list of event name strings.
        """
        return list(self._listeners.keys())


# Global platform event bus instance
platform_bus = EventBus()
