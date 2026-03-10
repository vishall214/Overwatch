"""
OVERWATCH — Alert Service
============================
Centralized alert management service that receives behavior events,
converts them into alerts, saves snapshots, and provides API access.

Phase 4: In-memory storage. Will be replaced by PostgreSQL later.
"""

import logging
import os
import threading
from datetime import datetime, timezone
from typing import Optional

import cv2
import numpy as np

from app.config import Settings
from app.models.events import Alert

logger = logging.getLogger(__name__)


class AlertService:
    """
    Manages alert creation, storage, and retrieval.

    Receives behavior events from the BehaviorWorker, converts them
    into Alert records, optionally saves a snapshot of the current frame,
    and stores alerts in-memory for API access.

    Attributes:
        _settings: Application configuration.
        _alerts: In-memory alert storage.
        _lock: Thread lock for safe concurrent access.
        _next_id: Auto-incrementing alert ID counter.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings: Settings = settings
        self._alerts: list[Alert] = []
        self._lock: threading.Lock = threading.Lock()
        self._next_id: int = 1

        os.makedirs(settings.snapshots_dir, exist_ok=True)

    def create_alert(
        self,
        event_type: str,
        track_id: Optional[int] = None,
        zone: str = "",
        metadata: Optional[dict] = None,
        frame: Optional[np.ndarray] = None,
    ) -> Alert:
        """
        Create and store a new alert from a behavior event.

        Args:
            event_type: Type of behavior event (intrusion, loitering, crowd).
            track_id: ID of the tracked object (if applicable).
            zone: Zone identifier where the event occurred.
            metadata: Additional context from the behavior event.
            frame: Current video frame for snapshot capture.

        Returns:
            Alert: The newly created alert.
        """
        now = datetime.now(timezone.utc)
        snapshot_path = ""

        if frame is not None:
            snapshot_path = self._save_snapshot(event_type, now, frame)

        with self._lock:
            alert = Alert(
                id=self._next_id,
                event_type=event_type,
                timestamp=now,
                track_id=track_id,
                zone=zone,
                metadata=metadata or {},
                snapshot_path=snapshot_path,
            )
            self._alerts.append(alert)
            self._next_id += 1

        logger.info(
            "Alert #%d created: %s track_id=%s zone=%s",
            alert.id, event_type, track_id, zone,
        )
        return alert

    def get_alerts(self, limit: int = 100) -> list[Alert]:
        """
        Retrieve recent alerts, newest first.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            list[Alert]: Recent alerts in reverse chronological order.
        """
        with self._lock:
            return list(reversed(self._alerts[-limit:]))

    def get_alert_count(self) -> int:
        """Return the total number of stored alerts."""
        with self._lock:
            return len(self._alerts)

    def _save_snapshot(
        self,
        event_type: str,
        timestamp: datetime,
        frame: np.ndarray,
    ) -> str:
        """
        Save a snapshot of the current frame to storage.

        Args:
            event_type: Type of event for the filename.
            timestamp: Alert timestamp for the filename.
            frame: BGR frame to save.

        Returns:
            str: Path to the saved snapshot, or empty string on failure.
        """
        time_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{event_type}_{time_str}.jpg"
        filepath = os.path.join(self._settings.snapshots_dir, filename)

        try:
            cv2.imwrite(filepath, frame)
            logger.debug("Snapshot saved: %s", filepath)
            return filepath
        except Exception:
            logger.exception("Failed to save snapshot: %s", filepath)
            return ""
