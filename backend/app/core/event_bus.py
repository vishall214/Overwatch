"""
OVERWATCH — Internal Event Bus
================================
Provides a simple synchronous/async publish-subscribe event bus
for decoupled service communication within the application.

Services subscribe to event types and receive published events
without direct coupling between producers and consumers.

Usage:
    bus = EventBus()
    bus.subscribe("FrameCaptured", handler_fn)
    await bus.publish(Event(type="FrameCaptured", data={...}))
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Union
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Type alias for event handlers (sync or async)
EventHandler = Union[
    Callable[["Event"], None],
    Callable[["Event"], Coroutine[Any, Any, None]],
]


@dataclass
class Event:
    """
    Represents an internal system event.

    Attributes:
        type: Event type identifier string (e.g. 'FrameCaptured', 'DetectionComplete').
        data: Arbitrary payload dictionary attached to the event.
        timestamp: UTC timestamp when the event was created.
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    """
    Simple internal event bus supporting synchronous and asynchronous handlers.

    Allows services to communicate through events rather than
    direct method calls, keeping modules decoupled.

    Methods:
        subscribe: Register a handler for an event type.
        unsubscribe: Remove a handler for an event type.
        publish: Dispatch an event to all subscribed handlers.
    """

    def __init__(self) -> None:
        """Initialize the event bus with an empty subscriber registry."""
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Register a handler for a specific event type.

        Args:
            event_type: The event type string to subscribe to.
            handler: Callable or coroutine to invoke when the event is published.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed %s to event '%s'", handler.__name__, event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Remove a handler from a specific event type.

        Args:
            event_type: The event type string to unsubscribe from.
            handler: The handler to remove.
        """
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h is not handler
            ]
            logger.debug("Unsubscribed %s from event '%s'", handler.__name__, event_type)

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all registered handlers for its type.

        Async handlers are awaited. Sync handlers are called directly.
        All handler exceptions are caught and logged to prevent
        one handler from breaking the event chain.

        Args:
            event: The Event instance to dispatch.
        """
        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            logger.debug("No handlers for event '%s'", event.type)
            return

        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception(
                    "Error in handler '%s' for event '%s'",
                    handler.__name__,
                    event.type,
                )
