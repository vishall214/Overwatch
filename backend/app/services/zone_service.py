"""
OVERWATCH — Zone Service
===========================
In-memory cache for user-defined behavior analysis zones.
Zones are loaded from the database once on startup and
reloaded after any create/delete operation. The pipeline
reads from the cache — no DB calls in the processing loop.
"""

import logging
from typing import Any

from app.database.database import SessionLocal
from app.database.models import Zone

logger = logging.getLogger(__name__)


class ZoneService:
    """
    Cached zone provider for the behavior pipeline.

    Attributes:
        _zones: In-memory list of zone dicts (read-only during pipeline).
    """

    def __init__(self) -> None:
        self._zones: list[dict[str, Any]] = []

    def load_zones(self) -> None:
        """Load all active zones from the database into memory."""
        db = SessionLocal()
        try:
            rows = db.query(Zone).filter(Zone.is_active == True).all()  # noqa: E712
            self._zones = [
                {
                    "id": r.id,
                    "name": r.name or f"Zone {r.id}",
                    "type": r.type,
                    "x": r.x,
                    "y": r.y,
                    "width": r.width,
                    "height": r.height,
                    "camera_id": r.camera_id,
                }
                for r in rows
            ]
            logger.info("ZoneService loaded %d zones", len(self._zones))
        finally:
            db.close()

    def get_zones(self) -> list[dict[str, Any]]:
        """Return the cached zone list (no DB call)."""
        return self._zones

    def reload(self) -> None:
        """Re-read zones from the database (call after create/delete)."""
        self.load_zones()
