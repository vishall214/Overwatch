"""
OVERWATCH — Alert Service
============================
Centralized alert management service that receives behavior events,
converts them into alerts, saves snapshots, and provides API access.

Phase 5: PostgreSQL persistence via SQLAlchemy.
"""

import logging
import os
import threading
import time as _time
from datetime import datetime, timezone
from typing import Any, Optional

import cv2
import numpy as np

from app.config import Settings
from app.database.database import SessionLocal
from app.database.crud import create_alert_row, get_recent_alerts, get_alert_count

logger = logging.getLogger(__name__)


class AlertService:
    """
    Manages alert creation, storage, and retrieval.

    Receives behavior events from the BehaviorWorker, converts them
    into Alert records, saves snapshots, and persists alerts to
    PostgreSQL.

    Attributes:
        _settings: Application configuration.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings: Settings = settings
        os.makedirs(settings.snapshots_dir, exist_ok=True)
        # In-memory duplicate suppression keyed by event/zone/object identity.
        self._recent_alerts: dict[str, float] = {}
        self._duplicate_window: float = float(settings.alert_duplicate_window_seconds)
        self._recent_alerts_lock = threading.Lock()
        self._snapshot_cleanup_counter: int = 0
        self._snapshot_lock = threading.Lock()

        # Keep snapshot storage bounded to avoid unbounded disk growth.
        self._snapshot_retention_max_files = max(
            1,
            int(settings.snapshot_retention_max_files),
        )
        self._snapshot_cleanup_every_alerts = max(
            1,
            int(settings.snapshot_cleanup_every_alerts),
        )

    @staticmethod
    def _normalize_text_key(value: Any, default: str = "unknown") -> str:
        text = str(value or "").strip().lower()
        return text if text else default

    def _build_dedup_key(
        self,
        event_type: str,
        zone: str,
        track_id: Optional[int],
        metadata: Optional[dict[str, Any]],
    ) -> str:
        payload = metadata or {}

        zone_key = payload.get("zone_id")
        if zone_key is None:
            zone_key = payload.get("zone")
        if zone_key is None:
            zone_key = zone

        object_key: Any = track_id
        if object_key is None:
            object_key = payload.get("track_id")
        if object_key is None:
            object_key = payload.get("object_id")
        if object_key is None:
            object_key = payload.get("object_type")
        if object_key is None:
            object_key = payload.get("class_name")

        return "|".join(
            [
                self._normalize_text_key(event_type),
                self._normalize_text_key(zone_key),
                self._normalize_text_key(object_key, default="none"),
            ]
        )

    def _is_duplicate_within_window(self, dedup_key: str) -> bool:
        now_mono = _time.monotonic()
        with self._recent_alerts_lock:
            # Opportunistically prune stale dedup keys.
            prune_before = now_mono - (self._duplicate_window * 3)
            stale_keys = [k for k, ts in self._recent_alerts.items() if ts < prune_before]
            for key in stale_keys:
                self._recent_alerts.pop(key, None)

            last_ts = self._recent_alerts.get(dedup_key, 0.0)
            if last_ts > 0 and (now_mono - last_ts) < self._duplicate_window:
                return True

            self._recent_alerts[dedup_key] = now_mono
            return False

    def create_alert(
        self,
        event_type: str,
        track_id: Optional[int] = None,
        zone: str = "",
        metadata: Optional[dict] = None,
        frame: Optional[np.ndarray] = None,
    ):
        """
        Create and persist a new alert from a behavior event.

        Args:
            event_type: Type of behavior event (intrusion, loitering, crowd).
            track_id: ID of the tracked object (if applicable).
            zone: Zone identifier where the event occurred.
            metadata: Additional context from the behavior event.
            frame: Current video frame for snapshot capture.

        Returns:
            AlertRow | None: The newly created database row, or None when suppressed.
        """
        now = datetime.now(timezone.utc)
        snapshot_path = ""

        dup_key = self._build_dedup_key(event_type, zone, track_id, metadata)
        if self._is_duplicate_within_window(dup_key):
            logger.debug(
                "Duplicate alert suppressed: type=%s zone=%s track=%s key=%s window=%.1fs",
                event_type,
                zone,
                track_id,
                dup_key,
                self._duplicate_window,
            )
            return None

        if frame is not None:
            snapshot_path = self._save_snapshot(event_type, now, frame)

        db = SessionLocal()
        try:
            alert = create_alert_row(
                db=db,
                event_type=event_type,
                track_id=track_id,
                zone=zone,
                snapshot_path=snapshot_path,
                metadata=metadata,
            )
            logger.info(
                "Alert #%d created: %s track_id=%s zone=%s",
                alert.id, event_type, track_id, zone,
            )
            return alert
        finally:
            db.close()

    def get_alerts(self, limit: int = 100):
        """
        Retrieve recent alerts from PostgreSQL, newest first.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            list[AlertRow]: Recent alerts in reverse chronological order.
        """
        db = SessionLocal()
        try:
            return get_recent_alerts(db, limit=limit)
        finally:
            db.close()

    def get_alert_count(self) -> int:
        """Return the total number of stored alerts."""
        db = SessionLocal()
        try:
            return get_alert_count(db)
        finally:
            db.close()

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
        time_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{event_type}_{time_str}.jpg"
        filepath = os.path.join(self._settings.snapshots_dir, filename)

        try:
            saved = cv2.imwrite(filepath, frame)
            if not saved:
                logger.error("OpenCV failed to encode snapshot: %s", filepath)
                return ""

            logger.debug("Snapshot saved: %s", filepath)

            with self._snapshot_lock:
                self._snapshot_cleanup_counter += 1
                if self._snapshot_cleanup_counter % self._snapshot_cleanup_every_alerts == 0:
                    self._enforce_snapshot_retention()

            # Store only filename for cross-platform portability.
            return filename
        except Exception:
            logger.exception("Failed to save snapshot: %s", filepath)
            return ""

    def _enforce_snapshot_retention(self) -> None:
        """Delete oldest snapshots when retention limit is exceeded."""
        try:
            files = []
            for name in os.listdir(self._settings.snapshots_dir):
                lower = name.lower()
                if not (lower.endswith(".jpg") or lower.endswith(".jpeg") or lower.endswith(".png")):
                    continue
                path = os.path.join(self._settings.snapshots_dir, name)
                if os.path.isfile(path):
                    files.append(path)

            if len(files) <= self._snapshot_retention_max_files:
                return

            files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            stale = files[self._snapshot_retention_max_files :]

            deleted = 0
            for path in stale:
                try:
                    os.remove(path)
                    deleted += 1
                except FileNotFoundError:
                    continue
                except OSError:
                    logger.warning("Failed deleting stale snapshot: %s", path)

            if deleted > 0:
                logger.info(
                    "Snapshot retention applied: deleted=%d kept=%d dir=%s",
                    deleted,
                    self._snapshot_retention_max_files,
                    self._settings.snapshots_dir,
                )
        except Exception:
            logger.exception("Snapshot retention pass failed")
