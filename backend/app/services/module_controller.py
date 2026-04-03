"""
OVERWATCH — Module Controller
================================
Runtime feature flags for analytics modules.
Controls which behavior analytics execute in the pipeline.

Supported modules:
    - intrusion : Intrusion zone detection
    - loitering : Loitering time detection
    - crowd     : Crowd count detection

State changes are thread-safe. Workers read module state as a
plain boolean dict snapshot — near-zero per-frame overhead.
"""

import logging
import threading
from typing import Dict

logger = logging.getLogger(__name__)

SUPPORTED_MODULES: frozenset = frozenset({"intrusion", "loitering", "crowd", "weapon_detection"})


class ModuleController:
    """
    Thread-safe controller for analytics module on/off state.

    Attributes:
        _lock: Mutex guarding _modules dict.
        _modules: Dict mapping module name → enabled flag.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._modules: Dict[str, bool] = {
            "intrusion": True,
            "loitering": True,
            "crowd": True,
            "weapon_detection": True,
        }
        logger.info(
            "ModuleController initialized — all modules enabled by default",
        )

    @property
    def modules(self) -> dict:
        """Return a point-in-time snapshot of all module states."""
        with self._lock:
            return dict(self._modules)

    def is_enabled(self, name: str) -> bool:
        """Return True if the named module is currently enabled."""
        with self._lock:
            return self._modules.get(name, False)

    def enable(self, name: str) -> bool:
        """
        Enable a module.

        Args:
            name: Module identifier (must be in SUPPORTED_MODULES).

        Returns:
            True if the module exists and was updated, False if unknown.
        """
        if name not in SUPPORTED_MODULES:
            return False
        with self._lock:
            self._modules[name] = True
        logger.info("Module '%s' enabled", name)
        return True

    def disable(self, name: str) -> bool:
        """
        Disable a module.

        Args:
            name: Module identifier (must be in SUPPORTED_MODULES).

        Returns:
            True if the module exists and was updated, False if unknown.
        """
        if name not in SUPPORTED_MODULES:
            return False
        with self._lock:
            self._modules[name] = False
        logger.info("Module '%s' disabled", name)
        return True
