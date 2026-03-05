"""
OVERWATCH — FastAPI Dependency Injection
==========================================
Provides shared dependencies for route handlers using
FastAPI's Depends() mechanism.
"""

from functools import lru_cache

from app.config import Settings, get_settings
from app.core.event_bus import EventBus
from app.core.queues import PipelineQueues

# ── Singleton instances ──────────────────────────────────────────

_event_bus: EventBus | None = None
_pipeline_queues: PipelineQueues | None = None


@lru_cache
def get_cached_settings() -> Settings:
    """
    Return a cached Settings instance.

    Uses lru_cache to ensure settings are loaded once
    and reused across all dependency injections.

    Returns:
        Settings: Application configuration.
    """
    return get_settings()


def get_event_bus() -> EventBus:
    """
    Return the singleton EventBus instance.

    Creates the bus on first call, returns the same
    instance on subsequent calls.

    Returns:
        EventBus: The application event bus.
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def get_pipeline_queues() -> PipelineQueues:
    """
    Return the singleton PipelineQueues instance.

    Creates the queues on first call with fixed sizes.
    Returns the same instance on subsequent calls.

    Returns:
        PipelineQueues: Thread-safe inter-worker queues.
    """
    global _pipeline_queues
    if _pipeline_queues is None:
        _pipeline_queues = PipelineQueues()
    return _pipeline_queues
