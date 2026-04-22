"""
OVERWATCH — System Monitor Service
======================================
Read-only aggregation service that collects system health,
pipeline performance metrics, and alert statistics from
existing components.

This service never modifies pipeline state.
"""

import logging
import time
from typing import Optional

from sqlalchemy import func

from app.database.database import SessionLocal
from app.database.models import AlertRow
from app.services.module_controller import ModuleController

logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    Aggregates real-time system metrics from the pipeline,
    module controller, and database.

    All methods are read-only.

    Attributes:
        _pipeline: Reference to the VideoPipeline (may be None before init).
        _modules: Reference to the shared ModuleController.
    """

    def __init__(
        self,
        pipeline=None,
        module_controller: Optional[ModuleController] = None,
    ) -> None:
        self._pipeline = pipeline
        self._modules: Optional[ModuleController] = module_controller
        self._alerts_total_cache_value: int = 0
        self._alerts_total_cache_ts: float = 0.0
        self._alerts_total_cache_ttl_seconds: float = 2.0

    def set_pipeline(self, pipeline) -> None:
        """Late-bind the pipeline reference (set during startup)."""
        self._pipeline = pipeline

    def set_module_controller(self, module_controller: ModuleController) -> None:
        """Late-bind the module controller reference."""
        self._modules = module_controller

    # ─────────────────────────────────────────────────────────────
    # System status (enhanced)
    # ─────────────────────────────────────────────────────────────

    def get_system_status(self) -> dict:
        """
        Aggregated system status for the dashboard.

        Returns dict with camera_running, pipeline_fps,
        active_modules, and alerts_total.
        """
        camera_running = False
        pipeline_fps = 0.0

        if self._pipeline is not None:
            camera_running = self._pipeline.is_running
            stats = self._pipeline.stats
            # Estimate FPS from inference worker avg_inference_ms
            avg_ms = stats.get("inference_worker", {}).get("avg_inference_ms", 0.0)
            if avg_ms > 0:
                pipeline_fps = round(1000.0 / avg_ms, 1)

        active_modules = (
            self._modules.modules if self._modules is not None
            else {
                "intrusion": True,
                "loitering": True,
                "crowd": True,
                "weapon_detection": True,
            }
        )

        return {
            "camera_running": camera_running,
            "pipeline_fps": pipeline_fps,
            "active_modules": active_modules,
            "alerts_total": self._get_total_alert_count(),
        }

    # ─────────────────────────────────────────────────────────────
    # Pipeline metrics
    # ─────────────────────────────────────────────────────────────

    def get_pipeline_metrics(self) -> dict:
        """
        Detailed per-stage pipeline metrics and queue fill levels.
        """
        if self._pipeline is None:
            return self._empty_metrics()

        stats = self._pipeline.stats
        return {
            "capture": stats.get("capture_worker", {}),
            "inference": stats.get("inference_worker", {}),
            "tracking": stats.get("tracking_worker", {}),
            "behavior": stats.get("behavior_worker", {}),
            "stream": stats.get("stream_worker", {}),
            "queues": stats.get("queues", {}),
        }

    # ─────────────────────────────────────────────────────────────
    # Alert statistics
    # ─────────────────────────────────────────────────────────────

    def get_alert_stats(self) -> dict:
        """
        Aggregated alert counts grouped by event_type.
        """
        db = SessionLocal()
        try:
            rows = (
                db.query(AlertRow.event_type, func.count(AlertRow.id))
                .group_by(AlertRow.event_type)
                .all()
            )
            counts = {event_type: count for event_type, count in rows}
            legacy_weapon = counts.get("dangerous_object", 0)
            weapon_detected = counts.get("weapon_detected", 0) + legacy_weapon
            weapon_in_zone = counts.get("weapon_in_zone", 0)
            weapon_total = weapon_detected + weapon_in_zone
            total = sum(counts.values())
            return {
                "total_alerts": total,
                "intrusion": counts.get("intrusion", 0),
                "loitering": counts.get("loitering", 0),
                "crowd": counts.get("crowd", 0),
                "weapon_detected": weapon_detected,
                "weapon_in_zone": weapon_in_zone,
                # Keep legacy key for backward compatibility with older clients.
                "dangerous_object": weapon_total,
                "face_match": counts.get("face_match", 0),
            }
        finally:
            db.close()

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    def _get_total_alert_count(self) -> int:
        now = time.monotonic()
        if (now - self._alerts_total_cache_ts) < self._alerts_total_cache_ttl_seconds:
            return self._alerts_total_cache_value

        db = SessionLocal()
        try:
            value = db.query(func.count(AlertRow.id)).scalar() or 0
            self._alerts_total_cache_value = int(value)
            self._alerts_total_cache_ts = now
            return self._alerts_total_cache_value
        finally:
            db.close()

    @staticmethod
    def _empty_metrics() -> dict:
        return {
            "capture": {},
            "inference": {},
            "tracking": {},
            "behavior": {},
            "stream": {},
            "queues": {},
        }
