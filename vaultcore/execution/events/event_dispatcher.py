"""
EventDispatcher
---------------
Lightweight publish/subscribe bus for execution events.

Design
------
  - Thread-safe registration and dispatch
  - Handlers are called synchronously on the worker thread
  - GUI frameworks (tkinter, Qt) must marshal to the main thread themselves

Usage
-----
  dispatcher = EventDispatcher()
  dispatcher.subscribe(ProgressUpdatedEvent, my_handler)
  dispatcher.dispatch(ProgressUpdatedEvent(...))
"""

import threading
from collections import defaultdict
from typing import Callable, Dict, List, Type, Any


class EventDispatcher:
    """Thread-safe publish/subscribe event bus."""

    def __init__(self) -> None:
        self._handlers: Dict[Type, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: Type, handler: Callable) -> None:
        """Register a handler for a specific event type."""
        with self._lock:
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: Type, handler: Callable) -> None:
        with self._lock:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h is not handler
            ]

    def dispatch(self, event: Any) -> None:
        """Publish an event to all registered handlers."""
        with self._lock:
            handlers = list(self._handlers.get(type(event), []))
        for handler in handlers:
            try:
                handler(event)
            except Exception:                          # noqa: BLE001
                pass  # TODO: route to platform logger
