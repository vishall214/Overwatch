"""
OVERWATCH — Behavior Worker
================================
Background worker that pulls tracked packets from the
tracking queue, runs behavior analysis (intrusion detection),
publishes behavior events, draws zone overlays, and pushes
results into the behavior queue.

Designed to run in a dedicated thread so behavior analysis
does not block tracking or the asyncio event loop.

Architecture:
    tracking_queue → BehaviorAnalysis → behavior_queue → StreamWorker
"""

import asyncio
import logging
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

import cv2
import numpy as np

from app.config import Settings
from app.core.event_bus import EventBus, Event
from app.core.queues import PipelineQueues, TrackingPacket, BehaviorPacket
from app.services.alert_service import AlertService
from app.services.face.face_service import FaceService
from app.services.module_controller import ModuleController
from app.services.zone_service import ZoneService
from app.utils.geometry_utils import point_in_polygon, bbox_center, rect_intersects_bbox

logger = logging.getLogger(__name__)

# ── Event state engine constants ─────────────────────────────────
# Minimum consecutive frames before an event is considered stable
STABILITY_THRESHOLDS: dict[str, int] = {
    "intrusion": 3,
    "crowd": 5,
    # loitering is already time-based — no frame threshold needed
}

# Seconds before a new alert of the same (event_type, zone) can fire
COOLDOWN_SECONDS: dict[str, float] = {
    "intrusion": 15.0,
    "loitering": 20.0,
    "crowd": 25.0,
}

# Seconds after last detection before an event state entry is purged
EVENT_STATE_TTL: float = 45.0

# Small grace window before resetting loiter timers after zone exit.
# Prevents one-frame intersection flicker from causing false resets.
LOITER_EXIT_GRACE_SECONDS: float = 0.5


class BehaviorWorker:
    """
    Runs behavior analysis in a background thread.

    Reads TrackingPackets from the tracking queue, checks each
    tracked object against configured intrusion zones, detects
    loitering when objects remain inside a zone beyond a time
    threshold, detects crowd formation when person count in zone
    exceeds a threshold, publishes IntrusionDetected, LoiteringDetected,
    and CrowdDetected events, draws zone overlays and alerts on
    the frame, and enqueues BehaviorPackets for the stream worker.

    Attributes:
        _settings: Application configuration.
        _queues: Pipeline queues for inter-worker communication.
        _event_bus: Event bus for publishing behavior events.
        _zone_polygon: List of (x, y) tuples defining Zone A.
        _loiter_threshold: Seconds before loitering alert fires.
        _crowd_threshold: Person count before crowd alert fires.
        _thread: Background thread handle.
        _is_running: Whether the worker is actively processing.
        _analyze_count: Total frames analyzed.
        _active_intrusions: Set of track_ids currently inside the zone.
        _loiter_state: Maps track_id → entry timestamp (monotonic).
        _loiter_alerted: Set of track_ids that already triggered loitering.
        _crowd_alerted: Whether a crowd alert is currently active.
    """

    def __init__(
        self,
        settings: Settings,
        queues: PipelineQueues,
        event_bus: EventBus,
        alert_service: Optional[AlertService] = None,
        face_service: Optional[FaceService] = None,
        module_controller: Optional[ModuleController] = None,
        zone_service: Optional[ZoneService] = None,
    ) -> None:
        self._settings: Settings = settings
        self._queues: PipelineQueues = queues
        self._event_bus: EventBus = event_bus
        self._alert_service: Optional[AlertService] = alert_service
        self._face_service: Optional[FaceService] = face_service
        self._module_controller: Optional[ModuleController] = module_controller
        self._zone_service: Optional[ZoneService] = zone_service
        self._zone_polygon: list[tuple[float, float]] = [
            (float(p[0]), float(p[1])) for p in settings.zone_a
        ]
        self._loiter_threshold: float = settings.loiter_threshold
        self._crowd_threshold: int = settings.crowd_threshold
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._analyze_count: int = 0
        self._active_intrusions: set[int] = set()
        self._loiter_state: dict[str, float] = {}
        self._loiter_alerted: set[str] = set()
        self._loiter_grace_deadlines: dict[str, float] = {}
        self._loiter_exit_grace_seconds: float = LOITER_EXIT_GRACE_SECONDS
        self._crowd_alerted: bool = False
        self._crowd_alerted_zones: set[int] = set()
        self._face_match_alerted: set[int] = set()
        self._identity_cache: dict[int, dict] = {}
        self._pending_tracks: set[int] = set()
        self._face_queue: queue.Queue = queue.Queue(maxsize=32)
        self._face_thread: Optional[threading.Thread] = None
        self._alert_queue_maxsize: int = max(1, int(settings.alert_queue_maxsize))
        self._alert_queue_soft_limit: int = max(
            1,
            min(
                self._alert_queue_maxsize,
                int(round(self._alert_queue_maxsize * float(settings.alert_queue_soft_limit_ratio))),
            ),
        )
        self._alert_queue_warn_interval_seconds: float = float(
            settings.alert_queue_warn_interval_seconds,
        )
        # Drop-oldest keeps the freshest alerts under bursts.
        self._alert_drop_strategy: str = "drop_oldest"
        self._alert_queue: queue.Queue = queue.Queue(maxsize=self._alert_queue_maxsize)
        self._alert_thread: Optional[threading.Thread] = None
        self._alert_drop_count: int = 0
        self._alert_persist_count: int = 0
        self._last_alert_backlog_warn_ts: float = 0.0
        self._drop_count: int = 0
        self._avg_behavior_ms: float = 0.0
        self._avg_input_age_ms: float = 0.0
        # ── Weapon / Dangerous Object State ──────────────────────
        self._weapon_state: dict[str, dict] = {}
        self._weapon_cooldown: dict[str, float] = {}
        self._weapon_consecutive_threshold: int = settings.weapon_consecutive_threshold
        self._weapon_cooldown_seconds: float = settings.weapon_cooldown_seconds
        self._active_weapon_alerts: list[dict] = []  # For drawing on current frame

        # ── Event state engine ───────────────────────────────────
        # Keyed by event_key = "{event_type}_{zone_id}_{track_id}"
        # Value: {"first_seen": float, "last_seen": float,
        #         "stable_count": int, "last_alert_time": float}
        self._event_states: dict[str, dict] = {}

    def start(self) -> None:
        """Start the behavior worker in a background thread."""
        if self._is_running:
            logger.warning("BehaviorWorker already running")
            return

        if self._thread is not None and self._thread.is_alive():
            logger.warning("BehaviorWorker thread still alive; refusing duplicate start")
            return
        if self._face_thread is not None and self._face_thread.is_alive():
            logger.warning("FaceWorker thread still alive; refusing duplicate start")
            return
        if self._alert_thread is not None and self._alert_thread.is_alive():
            logger.warning("AlertWorker thread still alive; refusing duplicate start")
            return

        try:
            self._event_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._event_loop = None

        self._is_running = True
        self._analyze_count = 0
        self._active_intrusions.clear()
        self._loiter_state.clear()
        self._loiter_alerted.clear()
        self._loiter_grace_deadlines.clear()
        self._crowd_alerted = False
        self._crowd_alerted_zones.clear()
        self._face_match_alerted.clear()
        self._identity_cache.clear()
        self._pending_tracks.clear()
        self._event_states.clear()
        self._drop_count = 0
        self._avg_behavior_ms = 0.0
        self._weapon_state.clear()
        self._weapon_cooldown.clear()
        self._active_weapon_alerts.clear()
        self._avg_input_age_ms = 0.0
        self._alert_drop_count = 0
        self._alert_persist_count = 0
        self._last_alert_backlog_warn_ts = 0.0
        # Drain any stale items from the face queue
        while not self._face_queue.empty():
            try:
                self._face_queue.get_nowait()
            except queue.Empty:
                break
        while not self._alert_queue.empty():
            try:
                self._alert_queue.get_nowait()
            except queue.Empty:
                break
        # Start background face recognition thread only when feature is enabled
        if self._settings.enable_face_recognition and self._face_service is not None:
            self._face_thread = threading.Thread(
                target=self._face_worker_loop,
                name="FaceWorker",
                daemon=True,
            )
            self._face_thread.start()
        if self._alert_service is not None:
            self._alert_thread = threading.Thread(
                target=self._alert_worker_loop,
                name="AlertWorker",
                daemon=True,
            )
            self._alert_thread.start()
        self._thread = threading.Thread(
            target=self._behavior_loop,
            name="BehaviorWorker",
            daemon=True,
        )
        self._thread.start()
        logger.info("BehaviorWorker started")

    def stop(self) -> None:
        """Stop the behavior worker and wait for threads to finish."""
        self._is_running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("BehaviorWorker thread did not stop within timeout")
            else:
                self._thread = None
        if self._face_thread is not None:
            self._face_thread.join(timeout=5.0)
            if self._face_thread.is_alive():
                logger.warning("FaceWorker thread did not stop within timeout")
            else:
                self._face_thread = None
        if self._alert_thread is not None:
            self._alert_thread.join(timeout=8.0)
            if self._alert_thread.is_alive():
                logger.warning(
                    "AlertWorker thread did not stop within timeout (queue_depth=%d)",
                    self._alert_queue.qsize(),
                )
            else:
                self._alert_thread = None
        logger.info(
            "BehaviorWorker stopped (analyzed %d frames)", self._analyze_count,
        )

    def reset_event_state(self) -> None:
        """
        Clear all event and detection state.

        Called when the video source changes so that stale
        intrusion/loitering/crowd state from a previous source
        does not carry over.
        """
        self._active_intrusions.clear()
        self._loiter_state.clear()
        self._loiter_alerted.clear()
        self._loiter_grace_deadlines.clear()
        self._crowd_alerted = False
        self._crowd_alerted_zones.clear()
        self._event_states.clear()
        self._weapon_state.clear()
        self._weapon_cooldown.clear()
        self._active_weapon_alerts.clear()
        self._face_match_alerted.clear()
        self._identity_cache.clear()
        self._pending_tracks.clear()
        logger.info("BehaviorWorker event state reset")

    def _publish_event(self, event: Event) -> None:
        """Publish an event to the bus from a worker thread."""
        if self._event_loop is not None and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._event_bus.publish(event),
                self._event_loop,
            )
        else:
            logger.debug("No event loop available, skipping event publish")

    # ── Event state engine helpers ───────────────────────────────

    @staticmethod
    def _make_event_key(event_type: str, zone_id: str, track_id: int = 0) -> str:
        """Build a unique key for the event state dict.

        Key format: ``{event_type}_{zone_id}_{track_id}``
        """
        return f"{event_type}_{zone_id}_{track_id}"

    @staticmethod
    def _make_loiter_key(track_id: int, zone_id: str) -> str:
        """Build a loitering timer key scoped by track and zone."""
        return f"{track_id}:{zone_id}"

    @staticmethod
    def _track_id_from_loiter_key(loiter_key: str) -> int:
        """Extract track id from loiter key, returning -1 when malformed."""
        try:
            return int(loiter_key.split(":", 1)[0])
        except (TypeError, ValueError):
            return -1

    def _clear_loiter_track(self, track_id: int) -> None:
        """Clear loiter timer state for a track across all zones."""
        prefix = f"{track_id}:"
        stale_keys = [k for k in self._loiter_state if k.startswith(prefix)]
        for key in stale_keys:
            self._loiter_state.pop(key, None)
            self._loiter_alerted.discard(key)
            self._loiter_grace_deadlines.pop(key, None)

    def _prune_loiter_keys(
        self,
        track_id: int,
        active_keys: set[str],
        now: float,
    ) -> None:
        """
        Keep timers for currently intersecting loiter zones and reset exited zones.

        Uses a brief grace window to avoid timer flicker from transient geometry jitter.
        """
        prefix = f"{track_id}:"
        track_keys = [k for k in self._loiter_state if k.startswith(prefix)]
        has_active_loiter_zone = len(active_keys) > 0
        for key in track_keys:
            if key in active_keys:
                self._loiter_grace_deadlines.pop(key, None)
                continue

            if has_active_loiter_zone:
                # Track moved to a different loiter zone; reset old-zone timer immediately.
                self._loiter_state.pop(key, None)
                self._loiter_alerted.discard(key)
                self._loiter_grace_deadlines.pop(key, None)
                continue

            deadline = self._loiter_grace_deadlines.get(key)
            if deadline is None:
                self._loiter_grace_deadlines[key] = now + self._loiter_exit_grace_seconds
                continue

            if now >= deadline:
                self._loiter_state.pop(key, None)
                self._loiter_alerted.discard(key)
                self._loiter_grace_deadlines.pop(key, None)

    def _has_met_loiter_threshold(self, duration: float) -> bool:
        """Return True only when elapsed duration has strictly reached threshold."""
        return duration >= self._loiter_threshold

    def _update_event_state(
        self, event_key: str, now: float,
    ) -> dict:
        """Insert or update an event state entry and return it."""
        state = self._event_states.get(event_key)
        if state is None:
            state = {
                "first_seen": now,
                "last_seen": now,
                "stable_count": 1,
                "last_alert_time": 0.0,
            }
            self._event_states[event_key] = state
        else:
            state["last_seen"] = now
            state["stable_count"] += 1
        return state

    def _should_trigger_alert(
        self, event_type: str, state: dict, now: float,
    ) -> bool:
        """Check both stability threshold and cooldown for an event.

        Returns True only when:
        1. ``stable_count >= STABILITY_THRESHOLDS[event_type]``  (default 1)
        2. ``now - last_alert_time >= COOLDOWN_SECONDS[event_type]``
        """
        threshold = STABILITY_THRESHOLDS.get(event_type, 1)
        if state["stable_count"] < threshold:
            return False

        cooldown = COOLDOWN_SECONDS.get(event_type, 15.0)
        if state["last_alert_time"] > 0 and (now - state["last_alert_time"]) < cooldown:
            return False

        return True

    def _cleanup_stale_events(self, now: float) -> None:
        """Remove event state entries unseen for longer than EVENT_STATE_TTL."""
        stale_keys = [
            k for k, v in self._event_states.items()
            if (now - v["last_seen"]) > EVENT_STATE_TTL
        ]
        for k in stale_keys:
            del self._event_states[k]

    def _compute_threat(self, signals: dict[str, bool]) -> int:
        """Compute threat score from frame-level signals and configured bonuses."""
        if not self._settings.enable_threat_scoring:
            return 0

        score = 0

        if signals.get("weapon_detected", False):
            score += int(self._settings.threat_weight_weapon_detected)
        if signals.get("weapon_in_zone", False):
            score += int(self._settings.threat_weight_weapon_in_zone)
        if signals.get("intrusion", False):
            score += int(self._settings.threat_weight_intrusion)
        if signals.get("loitering", False):
            score += int(self._settings.threat_weight_loitering)
        if signals.get("crowd", False):
            score += int(self._settings.threat_weight_crowd)

        # Context bonuses
        if signals.get("weapon_in_zone", False):
            score += int(self._settings.threat_bonus_weapon_zone)
        if signals.get("crowd", False) and (
            signals.get("weapon_detected", False)
            or signals.get("weapon_in_zone", False)
        ):
            score += int(self._settings.threat_bonus_weapon_crowd)
        if signals.get("intrusion", False) and (
            signals.get("weapon_detected", False)
            or signals.get("weapon_in_zone", False)
        ):
            score += int(self._settings.threat_bonus_intrusion_weapon)

        return max(0, min(100, int(round(score))))

    def _get_threat_level(self, score: int) -> str:
        """Map threat score to a normalized threat level string."""
        if score >= 76:
            return "CRITICAL"
        if score >= 51:
            return "HIGH"
        if score >= 26:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _attach_threat_context(
        event_data: dict[str, Any],
        threat_score: int,
        threat_level: str,
        signals: Optional[dict[str, bool]] = None,
    ) -> None:
        """Attach threat score/level metadata to an event payload in-place."""
        event_data["threat_score"] = int(threat_score)
        event_data["threat_level"] = str(threat_level)
        if signals is not None:
            event_data["threat_signals"] = {
                "weapon_detected": bool(signals.get("weapon_detected", False)),
                "weapon_in_zone": bool(signals.get("weapon_in_zone", False)),
                "intrusion": bool(signals.get("intrusion", False)),
                "loitering": bool(signals.get("loitering", False)),
                "crowd": bool(signals.get("crowd", False)),
            }

    def _flush_pending_alerts(
        self,
        pending_alerts: list[dict[str, Any]],
        frame: np.ndarray,
        threat_score: int,
        threat_level: str,
        signals: dict[str, bool],
    ) -> None:
        """Persist queued alerts after threat context is computed for the frame."""
        if self._alert_service is None:
            return

        frame_snapshot = frame.copy()

        for pending in pending_alerts:
            metadata = pending.get("metadata")
            if isinstance(metadata, dict):
                self._attach_threat_context(metadata, threat_score, threat_level, signals)
            else:
                metadata = {
                    "threat_score": int(threat_score),
                    "threat_level": str(threat_level),
                    "threat_signals": {
                        "weapon_detected": bool(signals.get("weapon_detected", False)),
                        "weapon_in_zone": bool(signals.get("weapon_in_zone", False)),
                        "intrusion": bool(signals.get("intrusion", False)),
                        "loitering": bool(signals.get("loitering", False)),
                        "crowd": bool(signals.get("crowd", False)),
                    },
                }

            self._enqueue_alert(
                event_type=str(pending.get("event_type", "unknown")),
                track_id=pending.get("track_id"),
                zone=str(pending.get("zone", "")),
                metadata=metadata,
                frame=frame_snapshot,
            )

    def _maybe_log_alert_queue_backlog(self, current_depth: int) -> None:
        """Emit throttled warnings when the alert queue nears capacity."""
        if current_depth < self._alert_queue_soft_limit:
            return

        now = time.monotonic()
        if (now - self._last_alert_backlog_warn_ts) < self._alert_queue_warn_interval_seconds:
            return

        self._last_alert_backlog_warn_ts = now
        logger.warning(
            "Alert queue backlog depth=%d/%d soft_limit=%d strategy=%s",
            current_depth,
            self._alert_queue_maxsize,
            self._alert_queue_soft_limit,
            self._alert_drop_strategy,
        )

    def _enqueue_alert(
        self,
        event_type: str,
        track_id: Optional[int],
        zone: str,
        metadata: dict[str, Any],
        frame: np.ndarray,
    ) -> None:
        """Queue alert persistence so DB/snapshot I/O never blocks behavior analysis."""
        if self._alert_service is None:
            return

        payload = {
            "event_type": event_type,
            "track_id": track_id,
            "zone": zone,
            "metadata": dict(metadata),
            "frame": frame,
        }

        depth_before = self._alert_queue.qsize()
        self._maybe_log_alert_queue_backlog(depth_before)

        try:
            self._alert_queue.put_nowait(payload)
        except queue.Full:
            self._alert_drop_count += 1
            dropped_event_type = "unknown"
            try:
                dropped = self._alert_queue.get_nowait()
                if isinstance(dropped, dict):
                    dropped_event_type = str(dropped.get("event_type", "unknown"))
            except queue.Empty:
                pass

            try:
                self._alert_queue.put_nowait(payload)
                log_message = (
                    "Alert queue full depth=%d/%d; dropped oldest pending alert "
                    "type=%s and enqueued type=%s (strategy=%s dropped_total=%d)"
                )
                log_args = (
                    depth_before,
                    self._alert_queue_maxsize,
                    dropped_event_type,
                    event_type,
                    self._alert_drop_strategy,
                    self._alert_drop_count,
                )
                if self._alert_drop_count == 1 or self._alert_drop_count % 10 == 0:
                    logger.warning(log_message, *log_args)
                else:
                    logger.debug(log_message, *log_args)
            except queue.Full:
                logger.error(
                    "Alert queue remained full after drop-oldest fallback; skipped enqueue for type=%s (dropped_total=%d)",
                    event_type,
                    self._alert_drop_count,
                )

    def _alert_worker_loop(self) -> None:
        """Background thread that persists queued alerts."""
        logger.info(
            "AlertWorker thread started (queue_maxsize=%d, soft_limit=%d, strategy=%s)",
            self._alert_queue_maxsize,
            self._alert_queue_soft_limit,
            self._alert_drop_strategy,
        )
        while self._is_running or not self._alert_queue.empty():
            try:
                payload = self._alert_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                row = self._alert_service.create_alert(
                    event_type=str(payload.get("event_type", "unknown")),
                    track_id=payload.get("track_id"),
                    zone=str(payload.get("zone", "")),
                    metadata=payload.get("metadata"),
                    frame=payload.get("frame"),
                )
                if row is not None:
                    self._alert_persist_count += 1
            except Exception:
                logger.exception("AlertWorker failed to persist alert")

            self._maybe_log_alert_queue_backlog(self._alert_queue.qsize())

        logger.info(
            "AlertWorker thread stopped (persisted=%d dropped=%d remaining=%d)",
            self._alert_persist_count,
            self._alert_drop_count,
            self._alert_queue.qsize(),
        )

    def _face_worker_loop(self) -> None:
        """Background thread: dequeue person crops, run InsightFace, update caches."""
        logger.info("FaceWorker thread started")
        while self._is_running:
            try:
                track_id, person_crop, frame = self._face_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                faces = self._face_service.recognize_faces(person_crop)
                if not faces:
                    self._pending_tracks.discard(track_id)
                    continue

                top_face = faces[0]
                if top_face["name"] != "Unknown":
                    self._identity_cache[track_id] = {
                        "name": top_face["name"],
                        "confidence": top_face["confidence"],
                    }

                    # Fire face_match alert (once per track)
                    if track_id not in self._face_match_alerted:
                        self._face_match_alerted.add(track_id)
                        match_event = {
                            "name": top_face["name"],
                            "track_id": track_id,
                            "confidence": top_face["confidence"],
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        self._attach_threat_context(match_event, threat_score=0, threat_level="LOW")
                        self._publish_event(Event(
                            type="FaceMatchDetected",
                            data=match_event,
                        ))
                        if self._alert_service is not None:
                            self._enqueue_alert(
                                event_type="face_match",
                                track_id=track_id,
                                zone="",
                                metadata=match_event,
                                frame=frame.copy(),
                            )
                        logger.warning(
                            "FACE MATCH: %s (track #%d, dist=%.4f)",
                            top_face["name"], track_id, top_face["confidence"],
                        )
                else:
                    # Unknown face — allow re-queuing on future frames
                    self._pending_tracks.discard(track_id)
            except Exception:
                logger.exception("FaceWorker error on track #%d", track_id)
                self._pending_tracks.discard(track_id)

        logger.info("FaceWorker thread stopped")

    def _behavior_loop(self) -> None:
        """
        Main behavior analysis loop running in a background thread.

        Pulls TrackingPackets from the tracking queue, checks each
        tracked object for zone intrusion, draws overlays, and
        pushes BehaviorPackets to the behavior queue.
        """
        logger.info(
            "Behavior loop started (zone_a=%s, loiter_threshold=%.1fs, crowd_threshold=%d)",
            self._zone_polygon, self._loiter_threshold, self._crowd_threshold,
        )

        while self._is_running:
            try:
                try:
                    packet: TrackingPacket = self._queues.tracking_queue.get(
                        timeout=0.1,
                    )
                except queue.Empty:
                    continue

                start_time = time.monotonic()
                input_age_ms = (time.monotonic_ns() - packet.timestamp_ns) / 1_000_000

                behavior_events: list[dict] = []
                pending_alerts: list[dict[str, Any]] = []
                intrusion_detected = False
                loitering_detected = False
                crowd_detected = False
                people_in_zone = 0
                loiter_timers: dict[int, float] = {}
                now = time.monotonic()
                current_track_ids: set[int] = set()

                # Snapshot module states once per packet — plain dict read,
                # zero-cost boolean checks inside the loop.
                _mod = (
                    self._module_controller.modules
                    if self._module_controller is not None
                    else {
                        "intrusion": True,
                        "loitering": True,
                        "crowd": True,
                        "weapon_detection": True,
                    }
                )

                # --- Resolve zones (cached — no DB call) ---------------
                user_zones: list[dict] = []
                if self._zone_service is not None:
                    user_zones = self._zone_service.get_zones()
                use_legacy = len(user_zones) == 0

                frame_h, frame_w = packet.frame.shape[:2]
                zone_debug_enabled = self._settings.debug_zone_logs
                should_log_zone_frame = zone_debug_enabled and (packet.frame_index % 30 == 0)

                if should_log_zone_frame:
                    logger.info(
                        "ZONE DEBUG FRAME: frame=%d frame_w=%d frame_h=%d zones=%s",
                        packet.frame_index,
                        frame_w,
                        frame_h,
                        [
                            {
                                "id": z.get("id"),
                                "type": z.get("type"),
                                "x": round(float(z.get("x", 0.0)), 4),
                                "y": round(float(z.get("y", 0.0)), 4),
                                "w": round(float(z.get("width", 0.0)), 4),
                                "h": round(float(z.get("height", 0.0)), 4),
                            }
                            for z in user_zones
                        ],
                    )

                # Per-zone counters for crowd detection
                people_per_zone: dict[int, int] = {}

                # --- Check each tracked object against zones ----------
                for obj in packet.tracked_objects:
                    bbox = obj["bbox"]
                    det_bbox_norm = [
                        bbox[0] / frame_w,
                        bbox[1] / frame_h,
                        bbox[2] / frame_w,
                        bbox[3] / frame_h,
                    ]

                    if should_log_zone_frame:
                        logger.info(
                            "DETECTION BBOX: track=%d bbox_px=[%.1f, %.1f, %.1f, %.1f] bbox_norm=[%.4f, %.4f, %.4f, %.4f]",
                            obj["track_id"],
                            bbox[0],
                            bbox[1],
                            bbox[2],
                            bbox[3],
                            det_bbox_norm[0],
                            det_bbox_norm[1],
                            det_bbox_norm[2],
                            det_bbox_norm[3],
                        )

                    center = bbox_center(bbox)
                    track_id = obj["track_id"]
                    current_track_ids.add(track_id)
                    is_person = obj.get("class_name", "unknown") == "person"
                    active_loiter_keys: set[str] = set()

                    in_any_zone = False

                    if use_legacy:
                        # ---------- Legacy polygon fallback ----------
                        if point_in_polygon(center, self._zone_polygon):
                            in_any_zone = True
                            if is_person:
                                people_in_zone += 1

                            # -- Intrusion (legacy) --
                            if _mod["intrusion"]:
                                intrusion_detected = True
                                ekey = self._make_event_key("intrusion", "A", track_id)
                                state = self._update_event_state(ekey, now)
                                if self._should_trigger_alert("intrusion", state, now):
                                    state["last_alert_time"] = now
                                    self._active_intrusions.add(track_id)
                                    event_data = {
                                        "track_id": track_id,
                                        "zone": "A",
                                        "class_name": obj.get("class_name", "unknown"),
                                        "bbox": bbox,
                                        "timestamp": datetime.now(timezone.utc).isoformat(),
                                    }
                                    behavior_events.append(event_data)
                                    self._publish_event(Event(type="IntrusionDetected", data=event_data))
                                    pending_alerts.append({
                                        "event_type": "intrusion",
                                        "track_id": track_id,
                                        "zone": "A",
                                        "metadata": event_data,
                                    })
                                    logger.warning("INTRUSION: %s #%d entered Zone A", obj.get("class_name", "unknown"), track_id)
                            else:
                                self._active_intrusions.discard(track_id)

                            # -- Loitering (legacy) --
                            if _mod["loitering"]:
                                loiter_key = self._make_loiter_key(track_id, "A")
                                active_loiter_keys.add(loiter_key)
                                if loiter_key not in self._loiter_state:
                                    self._loiter_state[loiter_key] = now
                                duration = now - self._loiter_state[loiter_key]
                                loiter_timers[track_id] = max(loiter_timers.get(track_id, 0.0), duration)
                                if self._has_met_loiter_threshold(duration):
                                    loitering_detected = True
                                    ekey = self._make_event_key("loitering", "A", track_id)
                                    state = self._update_event_state(ekey, now)
                                    if self._should_trigger_alert("loitering", state, now):
                                        state["last_alert_time"] = now
                                        self._loiter_alerted.add(loiter_key)
                                        loiter_event = {
                                            "track_id": track_id, "duration": round(duration, 1),
                                            "zone": "A", "class_name": obj.get("class_name", "unknown"),
                                            "timestamp": datetime.now(timezone.utc).isoformat(),
                                        }
                                        behavior_events.append(loiter_event)
                                        self._publish_event(Event(type="LoiteringDetected", data=loiter_event))
                                        pending_alerts.append({
                                            "event_type": "loitering",
                                            "track_id": track_id,
                                            "zone": "A",
                                            "metadata": loiter_event,
                                        })
                                        logger.warning("LOITERING: %s #%d in Zone A for %.1fs", obj.get("class_name", "unknown"), track_id, duration)
                            else:
                                self._clear_loiter_track(track_id)
                    else:
                        # ---------- User-defined rectangular zones ----------
                        for zone in user_zones:
                            zone_bbox_px = [
                                zone["x"] * frame_w,
                                zone["y"] * frame_h,
                                (zone["x"] + zone["width"]) * frame_w,
                                (zone["y"] + zone["height"]) * frame_h,
                            ]
                            intersects = rect_intersects_bbox(zone, bbox, frame_w, frame_h)

                            if should_log_zone_frame:
                                logger.info(
                                    "ZONE: id=%d type=%s bbox_norm=[%.4f, %.4f, %.4f, %.4f] bbox_px=[%.1f, %.1f, %.1f, %.1f]",
                                    zone["id"],
                                    zone["type"],
                                    zone["x"],
                                    zone["y"],
                                    zone["x"] + zone["width"],
                                    zone["y"] + zone["height"],
                                    zone_bbox_px[0],
                                    zone_bbox_px[1],
                                    zone_bbox_px[2],
                                    zone_bbox_px[3],
                                )
                                logger.info(
                                    "INTERSECTION INPUTS: zone_bbox_px=[%.1f, %.1f, %.1f, %.1f] detection_bbox_px=[%.1f, %.1f, %.1f, %.1f] intersects=%s",
                                    zone_bbox_px[0],
                                    zone_bbox_px[1],
                                    zone_bbox_px[2],
                                    zone_bbox_px[3],
                                    bbox[0],
                                    bbox[1],
                                    bbox[2],
                                    bbox[3],
                                    intersects,
                                )

                            if not intersects:
                                continue
                            in_any_zone = True
                            zone_name = zone.get("name", f"Zone {zone['id']}")
                            zone_type = zone["type"]
                            zone_id = zone["id"]

                            if is_person:
                                people_per_zone[zone_id] = people_per_zone.get(zone_id, 0) + 1

                            # -- Intrusion (user zone) --
                            if zone_type == "intrusion" and _mod["intrusion"]:
                                intrusion_detected = True
                                ekey = self._make_event_key("intrusion", str(zone_id), track_id)
                                state = self._update_event_state(ekey, now)
                                if self._should_trigger_alert("intrusion", state, now):
                                    state["last_alert_time"] = now
                                    self._active_intrusions.add(track_id)
                                    event_data = {
                                        "track_id": track_id, "zone": zone_name,
                                        "class_name": obj.get("class_name", "unknown"),
                                        "bbox": bbox,
                                        "timestamp": datetime.now(timezone.utc).isoformat(),
                                    }
                                    behavior_events.append(event_data)
                                    self._publish_event(Event(type="IntrusionDetected", data=event_data))
                                    pending_alerts.append({
                                        "event_type": "intrusion",
                                        "track_id": track_id,
                                        "zone": zone_name,
                                        "metadata": event_data,
                                    })
                                    logger.warning("INTRUSION: %s #%d entered %s", obj.get("class_name", "unknown"), track_id, zone_name)

                            # -- Loitering (user zone) --
                            if zone_type == "loitering" and _mod["loitering"]:
                                loiter_key = self._make_loiter_key(track_id, str(zone_id))
                                active_loiter_keys.add(loiter_key)
                                if loiter_key not in self._loiter_state:
                                    self._loiter_state[loiter_key] = now
                                duration = now - self._loiter_state[loiter_key]
                                loiter_timers[track_id] = max(loiter_timers.get(track_id, 0.0), duration)
                                if self._has_met_loiter_threshold(duration):
                                    loitering_detected = True
                                    ekey = self._make_event_key("loitering", str(zone_id), track_id)
                                    state = self._update_event_state(ekey, now)
                                    if self._should_trigger_alert("loitering", state, now):
                                        state["last_alert_time"] = now
                                        self._loiter_alerted.add(loiter_key)
                                        loiter_event = {
                                            "track_id": track_id, "duration": round(duration, 1),
                                            "zone": zone_name, "class_name": obj.get("class_name", "unknown"),
                                            "timestamp": datetime.now(timezone.utc).isoformat(),
                                        }
                                        behavior_events.append(loiter_event)
                                        self._publish_event(Event(type="LoiteringDetected", data=loiter_event))
                                        pending_alerts.append({
                                            "event_type": "loitering",
                                            "track_id": track_id,
                                            "zone": zone_name,
                                            "metadata": loiter_event,
                                        })
                                        logger.warning("LOITERING: %s #%d in %s for %.1fs", obj.get("class_name", "unknown"), track_id, zone_name, duration)

                    if _mod["loitering"]:
                        self._prune_loiter_keys(track_id, active_loiter_keys, now)
                    else:
                        self._clear_loiter_track(track_id)

                    if not in_any_zone:
                        # Object left all zones
                        self._active_intrusions.discard(track_id)

                # --- Crowd detection (event-state-driven) ---------------
                if use_legacy:
                    if _mod["crowd"] and people_in_zone > self._crowd_threshold:
                        crowd_detected = True
                        ekey = self._make_event_key("crowd", "A", 0)
                        state = self._update_event_state(ekey, now)
                        if self._should_trigger_alert("crowd", state, now):
                            state["last_alert_time"] = now
                            self._crowd_alerted = True
                            crowd_event = {
                                "count": people_in_zone, "threshold": self._crowd_threshold,
                                "zone": "A", "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                            behavior_events.append(crowd_event)
                            self._publish_event(Event(type="CrowdDetected", data=crowd_event))
                            pending_alerts.append({
                                "event_type": "crowd",
                                "track_id": None,
                                "zone": "A",
                                "metadata": crowd_event,
                            })
                            logger.warning("CROWD: %d persons in Zone A (threshold %d)", people_in_zone, self._crowd_threshold)
                    else:
                        self._crowd_alerted = False
                else:
                    for zone in user_zones:
                        if zone["type"] != "crowd":
                            continue
                        zid = zone["id"]
                        z_count = people_per_zone.get(zid, 0)
                        zone_name = zone.get("name", f"Zone {zid}")
                        if _mod["crowd"] and z_count > self._crowd_threshold:
                            crowd_detected = True
                            ekey = self._make_event_key("crowd", str(zid), 0)
                            state = self._update_event_state(ekey, now)
                            if self._should_trigger_alert("crowd", state, now):
                                state["last_alert_time"] = now
                                self._crowd_alerted_zones.add(zid)
                                crowd_event = {
                                    "count": z_count, "threshold": self._crowd_threshold,
                                    "zone": zone_name, "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                                behavior_events.append(crowd_event)
                                self._publish_event(Event(type="CrowdDetected", data=crowd_event))
                                pending_alerts.append({
                                    "event_type": "crowd",
                                    "track_id": None,
                                    "zone": zone_name,
                                    "metadata": crowd_event,
                                })
                                logger.warning("CROWD: %d persons in %s (threshold %d)", z_count, zone_name, self._crowd_threshold)
                        else:
                            self._crowd_alerted_zones.discard(zid)

                # Clean up state for tracks that disappeared
                stale_track_ids = {
                    self._track_id_from_loiter_key(key)
                    for key in self._loiter_state.keys()
                    if self._track_id_from_loiter_key(key) not in current_track_ids
                }
                for tid in stale_track_ids:
                    if tid < 0:
                        continue
                    self._clear_loiter_track(tid)
                    self._active_intrusions.discard(tid)

                # Clean up stale event states (memory leak prevention)
                self._cleanup_stale_events(now)

                # --- Face recognition (disabled when enable_face_recognition=False) ---
                face_results: list[dict] = []

                if self._settings.enable_face_recognition:
                    for obj in packet.tracked_objects:
                        track_id = obj["track_id"]

                        # Use cached identity if available
                        if track_id in self._identity_cache:
                            cached = self._identity_cache[track_id]
                            face_results.append({
                                "bbox": obj["bbox"],
                                "name": cached["name"],
                                "confidence": cached["confidence"],
                            })
                            continue

                        # Skip non-persons and already-pending tracks
                        if obj.get("class_name", "unknown") != "person":
                            continue
                        if track_id in self._pending_tracks:
                            continue
                        if self._face_service is None or not self._face_service.is_loaded:
                            continue

                        # Crop the person region and enqueue for background recognition
                        bx = obj["bbox"]
                        cx1 = max(0, int(bx[0]))
                        cy1 = max(0, int(bx[1]))
                        cx2 = min(packet.frame.shape[1], int(bx[2]))
                        cy2 = min(packet.frame.shape[0], int(bx[3]))
                        if cx2 - cx1 < 20 or cy2 - cy1 < 20:
                            continue
                        person_crop = packet.frame[cy1:cy2, cx1:cx2].copy()

                        try:
                            self._face_queue.put_nowait((
                                track_id, person_crop, packet.frame,
                            ))
                            self._pending_tracks.add(track_id)
                        except queue.Full:
                            pass  # Drop — the person will be re-queued next frame

                    # Clean up caches for tracks that disappeared
                    stale_face_ids = self._face_match_alerted - current_track_ids
                    self._face_match_alerted -= stale_face_ids
                    for tid in list(self._identity_cache.keys()):
                        if tid not in current_track_ids:
                            del self._identity_cache[tid]
                    self._pending_tracks -= (self._pending_tracks - current_track_ids)

                # --- Weapon / Dangerous Object Handling ---------------
                weapon_detected = False
                weapon_signal_detected = any(
                    alert.get("event_type") in {"weapon_detected", "weapon_in_zone"}
                    for alert in self._active_weapon_alerts
                )
                weapon_in_zone_detected = any(
                    alert.get("event_type") == "weapon_in_zone"
                    for alert in self._active_weapon_alerts
                )

                if _mod.get("weapon_detection", True):
                    weapon_dets = getattr(packet, "weapon_detections", None)
                    if weapon_dets is not None:
                        if weapon_dets:
                            weapon_signal_detected = True
                            for det in weapon_dets:
                                bbox = det.get("bbox", [0, 0, 0, 0])
                                bbox_norm = self._normalize_bbox(bbox, frame_w, frame_h)
                                bbox_px = self._to_pixel_bbox(bbox_norm, frame_w, frame_h)
                                in_zone, _, _ = self._resolve_weapon_zone(
                                    bbox_px=bbox_px,
                                    user_zones=user_zones,
                                    frame_w=frame_w,
                                    frame_h=frame_h,
                                    use_legacy=use_legacy,
                                )
                                if in_zone:
                                    weapon_in_zone_detected = True

                        weapon_detected = self._handle_weapon_detections(
                            weapon_dets,
                            now,
                            packet.frame,
                            behavior_events,
                            user_zones=user_zones,
                            frame_w=frame_w,
                            frame_h=frame_h,
                            use_legacy=use_legacy,
                            pending_alerts=pending_alerts,
                        )
                        if weapon_detected or self._active_weapon_alerts:
                            weapon_signal_detected = True
                        if any(
                            alert.get("event_type") == "weapon_in_zone"
                            for alert in self._active_weapon_alerts
                        ):
                            weapon_in_zone_detected = True

                threat_signals = {
                    "weapon_detected": weapon_signal_detected,
                    "weapon_in_zone": weapon_in_zone_detected,
                    "intrusion": intrusion_detected,
                    "loitering": loitering_detected,
                    "crowd": crowd_detected,
                }
                threat_score = self._compute_threat(threat_signals)
                threat_level = self._get_threat_level(threat_score)

                for event_data in behavior_events:
                    self._attach_threat_context(event_data, threat_score, threat_level, threat_signals)

                if pending_alerts:
                    self._flush_pending_alerts(
                        pending_alerts=pending_alerts,
                        frame=packet.frame,
                        threat_score=threat_score,
                        threat_level=threat_level,
                        signals=threat_signals,
                    )

                # --- Draw zone overlay and alerts ---------------------
                annotated = self._draw_zone_overlay(
                    packet.annotated_frame,
                    intrusion_detected,
                    loitering_detected,
                    crowd_detected,
                    people_in_zone,
                    loiter_timers,
                    weapon_detected=(weapon_detected or bool(self._active_weapon_alerts)),
                    weapon_in_zone_detected=weapon_in_zone_detected,
                    user_zones=user_zones,
                )

                # --- Draw face identity overlays ----------------------
                annotated = self._draw_face_overlays(annotated, face_results)

                # --- Draw weapon overlays LAST (highest priority) ------
                # Rendered after all other overlays to ensure weapon
                # bounding boxes and banners are always on top.
                if weapon_detected or self._active_weapon_alerts:
                    annotated = self._draw_weapon_overlays(annotated)

                behavior_time_ms = (time.monotonic() - start_time) * 1000

                behavior_packet = BehaviorPacket(
                    frame=packet.frame,
                    annotated_frame=annotated,
                    tracked_objects=packet.tracked_objects,
                    behavior_events=behavior_events,
                    frame_index=packet.frame_index,
                    timestamp_ns=packet.timestamp_ns,
                    capture_time_ms=packet.capture_time_ms,
                    inference_time_ms=packet.inference_time_ms,
                    tracking_time_ms=packet.tracking_time_ms,
                    behavior_time_ms=round(behavior_time_ms, 1),
                )

                self._analyze_count += 1
                alpha = 0.1
                if self._analyze_count == 1:
                    self._avg_behavior_ms = behavior_time_ms
                    self._avg_input_age_ms = input_age_ms
                else:
                    self._avg_behavior_ms = (
                        alpha * behavior_time_ms + (1 - alpha) * self._avg_behavior_ms
                    )
                    self._avg_input_age_ms = (
                        alpha * input_age_ms + (1 - alpha) * self._avg_input_age_ms
                    )

                try:
                    self._queues.behavior_queue.put_nowait(behavior_packet)
                except queue.Full:
                    self._drop_count += 1
                    try:
                        self._queues.behavior_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queues.behavior_queue.put_nowait(behavior_packet)
                    logger.debug(
                        "Behavior queue full, replaced oldest with frame %d",
                        packet.frame_index,
                    )

                if self._analyze_count % 30 == 0:
                    logger.info(
                        "perf behavior frame=%d input_age_ms=%.1f behavior_time_ms=%.1f behavior_queue=%d face_queue=%d threat_score=%d threat_level=%s",
                        packet.frame_index,
                        input_age_ms,
                        behavior_time_ms,
                        self._queues.behavior_queue.qsize(),
                        self._face_queue.qsize(),
                        threat_score,
                        threat_level,
                    )

            except Exception:
                logger.exception("Error in behavior loop")
                time.sleep(0.1)

        logger.info("Behavior loop exited")

    # Zone type → BGR colour map
    _ZONE_COLOURS: dict[str, tuple[int, int, int]] = {
        "intrusion": (0, 0, 255),     # red
        "loitering": (0, 165, 255),   # orange
        "crowd": (0, 255, 255),       # yellow
    }

    def _draw_zone_overlay(
        self,
        frame: np.ndarray,
        intrusion_detected: bool,
        loitering_detected: bool,
        crowd_detected: bool,
        people_in_zone: int,
        loiter_timers: dict[int, float],
        weapon_detected: bool = False,
        weapon_in_zone_detected: bool = False,
        user_zones: Optional[list[dict]] = None,
    ) -> np.ndarray:
        """
        Draw zone overlays, loiter timers, crowd count, and alert text.

        Supports both legacy polygon and user-defined rectangular zones.
        """
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        if user_zones:
            # ---------- Draw user-defined rectangular zones ----------
            overlay = annotated.copy()
            for zone in user_zones:
                zx1 = int(zone["x"] * w)
                zy1 = int(zone["y"] * h)
                zx2 = int((zone["x"] + zone["width"]) * w)
                zy2 = int((zone["y"] + zone["height"]) * h)
                colour = self._ZONE_COLOURS.get(zone["type"], (0, 255, 0))
                cv2.rectangle(overlay, (zx1, zy1), (zx2, zy2), colour, -1)
                cv2.rectangle(annotated, (zx1, zy1), (zx2, zy2), colour, 2)
                label = zone.get("name", f"Zone {zone['id']}")
                cv2.putText(
                    annotated, f"{label} [{zone['type']}]",
                    (zx1 + 5, zy1 + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1,
                )
            cv2.addWeighted(overlay, 0.15, annotated, 0.85, 0, annotated)
        else:
            # ---------- Legacy polygon fallback ----------
            pts = np.array(self._zone_polygon, dtype=np.int32).reshape((-1, 1, 2))
            zone_colour = (0, 0, 255) if intrusion_detected else (0, 255, 0)
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [pts], zone_colour)
            cv2.addWeighted(overlay, 0.2, annotated, 0.8, 0, annotated)
            cv2.polylines(annotated, [pts], isClosed=True, color=zone_colour, thickness=2)
            cv2.putText(
                annotated, "Zone A",
                (int(self._zone_polygon[0][0]) + 5, int(self._zone_polygon[0][1]) - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, zone_colour, 1,
            )

        # --- Alert text overlays ---
        y_offset = 30

        # Weapon alert (highest priority — rendered first at top)
        if weapon_detected:
            weapon_text = "!! WEAPON IN ZONE !!" if weapon_in_zone_detected else "!! WEAPON DETECTED !!"
            weapon_color = (0, 0, 255) if weapon_in_zone_detected else (182, 89, 155)
            cv2.putText(
                annotated, weapon_text, (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, weapon_color, 2,
            )
            y_offset += 35

        # Intrusion alert
        if intrusion_detected:
            cv2.putText(
                annotated, "INTRUSION DETECTED", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2,
            )
            y_offset += 35

        if loitering_detected:
            cv2.putText(
                annotated, "LOITERING DETECTED", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2,
            )
            y_offset += 35

        cv2.putText(
            annotated, f"People Count: {people_in_zone}", (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2,
        )
        y_offset += 30

        if crowd_detected:
            cv2.putText(
                annotated, "CROWD DETECTED", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2,
            )
            y_offset += 35

        for track_id, duration in loiter_timers.items():
            timer_text = f"LOITERING TIMER #{track_id}: {duration:.1f}s"
            cv2.putText(
                annotated, timer_text, (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2,
            )
            y_offset += 25

        return annotated

    @staticmethod
    def _draw_face_overlays(
        frame: np.ndarray,
        face_results: list[dict],
    ) -> np.ndarray:
        """
        Draw face identity labels on the frame.

        For each detected face, draws the name (or "Unknown Person")
        and confidence score near the face bounding box.

        Args:
            frame: Annotated frame (modified in-place).
            face_results: Results from FaceService.recognize_faces().

        Returns:
            np.ndarray: Frame with face identity labels.
        """
        if not face_results:
            return frame

        for fr in face_results:
            x1, y1, x2, y2 = (
                int(fr["bbox"][0]),
                int(fr["bbox"][1]),
                int(fr["bbox"][2]),
                int(fr["bbox"][3]),
            )
            name = fr["name"]
            dist = fr["confidence"]

            if name != "Unknown":
                label = f"Name: {name}"
                conf_label = f"Confidence: {dist:.2f}"
                colour = (0, 255, 0)
            else:
                label = "Unknown Person"
                conf_label = ""
                colour = (128, 128, 128)

            # Draw face bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 1)

            # Name label
            cv2.putText(
                frame, label, (x1, y2 + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1,
            )
            if conf_label:
                cv2.putText(
                    frame, conf_label, (x1, y2 + 36),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1,
                )

        return frame

    @staticmethod
    def _normalize_bbox(
        bbox: list[float],
        frame_w: int,
        frame_h: int,
    ) -> list[float]:
        """Return bbox as normalized [x1, y1, x2, y2] in [0, 1] range."""
        if len(bbox) != 4 or frame_w <= 0 or frame_h <= 0:
            return [0.0, 0.0, 0.0, 0.0]

        if max(bbox) <= 1.0:
            x1, y1, x2, y2 = bbox
        else:
            x1 = bbox[0] / frame_w
            y1 = bbox[1] / frame_h
            x2 = bbox[2] / frame_w
            y2 = bbox[3] / frame_h

        return [
            float(max(0.0, min(1.0, x1))),
            float(max(0.0, min(1.0, y1))),
            float(max(0.0, min(1.0, x2))),
            float(max(0.0, min(1.0, y2))),
        ]

    @staticmethod
    def _to_pixel_bbox(
        bbox_norm: list[float],
        frame_w: int,
        frame_h: int,
    ) -> list[float]:
        """Convert normalized bbox into pixel coordinates."""
        return [
            bbox_norm[0] * frame_w,
            bbox_norm[1] * frame_h,
            bbox_norm[2] * frame_w,
            bbox_norm[3] * frame_h,
        ]

    def _resolve_weapon_zone(
        self,
        bbox_px: list[float],
        user_zones: list[dict],
        frame_w: int,
        frame_h: int,
        use_legacy: bool,
    ) -> tuple[bool, Optional[str], str]:
        """Resolve whether a weapon bbox is inside a zone and return zone context."""
        if use_legacy:
            center = bbox_center(bbox_px)
            in_legacy = point_in_polygon(center, self._zone_polygon)
            return (in_legacy, "A" if in_legacy else None, "Zone A" if in_legacy else "")

        matched_zone: Optional[dict] = None
        best_iou = 0.0
        for zone in user_zones:
            if not rect_intersects_bbox(zone, bbox_px, frame_w, frame_h):
                continue

            zone_bbox_px = [
                zone["x"] * frame_w,
                zone["y"] * frame_h,
                (zone["x"] + zone["width"]) * frame_w,
                (zone["y"] + zone["height"]) * frame_h,
            ]
            overlap = self._bbox_iou(zone_bbox_px, bbox_px)
            if matched_zone is None or overlap > best_iou:
                matched_zone = zone
                best_iou = overlap

        if matched_zone is None:
            return False, None, ""

        zone_id = str(matched_zone.get("id"))
        zone_name = matched_zone.get("name", f"Zone {zone_id}")
        return True, zone_id, zone_name

    def _handle_weapon_detections(
        self,
        weapon_dets: list[dict],
        now: float,
        frame: np.ndarray,
        behavior_events: list[dict],
        user_zones: Optional[list[dict]] = None,
        frame_w: Optional[int] = None,
        frame_h: Optional[int] = None,
        use_legacy: Optional[bool] = None,
        pending_alerts: Optional[list[dict[str, Any]]] = None,
    ) -> bool:
        """
        Process weapon detections with temporal filtering and cooldown.

        Alerts are zone-aware:
        - weapon_in_zone: weapon intersects a zone (critical)
        - weapon_detected: weapon outside all zones (warning)

        Cooldown keys are scoped by:
        - class + zone_id when inside a zone
        - class only when outside all zones

        Args:
            weapon_dets: List of weapon detection dicts from the current frame.
                         Empty list means detection ran but found nothing.
            now: Current monotonic time.
            frame: Current video frame for snapshot capture.
            behavior_events: Mutable list to append behavior event dicts to.
            pending_alerts: Optional mutable list for deferred alert persistence.

        Returns:
            bool: True if any weapon alert was triggered this frame.
        """
        if frame_w is None:
            frame_w = int(frame.shape[1]) if frame.ndim >= 2 else 0
        if frame_h is None:
            frame_h = int(frame.shape[0]) if frame.ndim >= 2 else 0
        if user_zones is None:
            user_zones = []
        if use_legacy is None:
            use_legacy = len(user_zones) == 0

        alert_fired = False
        seen_keys: set[str] = set()

        for det in weapon_dets:
            class_name = det.get("class_name", "unknown")
            bbox = det.get("bbox", [0, 0, 0, 0])
            confidence = det.get("confidence", 0.0)

            bbox_norm = self._normalize_bbox(bbox, frame_w, frame_h)
            bbox_px = self._to_pixel_bbox(bbox_norm, frame_w, frame_h)
            in_zone, zone_id, zone_name = self._resolve_weapon_zone(
                bbox_px=bbox_px,
                user_zones=user_zones,
                frame_w=frame_w,
                frame_h=frame_h,
                use_legacy=use_legacy,
            )

            event_type = "weapon_in_zone" if in_zone else "weapon_detected"
            severity = "critical" if in_zone else "warning"
            key = (
                f"{class_name}_zone_{zone_id}"
                if in_zone and zone_id is not None
                else f"{class_name}_outside"
            )
            seen_keys.add(key)

            if key not in self._weapon_state:
                self._weapon_state[key] = {
                    "count": 0,
                    "confidence": 0.0,
                    "class_name": class_name,
                    "bbox": bbox_px,
                    "event_type": event_type,
                    "zone_id": zone_id,
                    "zone_name": zone_name,
                }

            state = self._weapon_state[key]
            state["count"] += 1
            state["confidence"] = confidence
            state["bbox"] = bbox_px
            state["event_type"] = event_type
            state["zone_id"] = zone_id
            state["zone_name"] = zone_name

            # Check if consecutive threshold is met
            if state["count"] >= self._weapon_consecutive_threshold:
                # Check cooldown
                last_alert_time = self._weapon_cooldown.get(key, 0.0)
                if now - last_alert_time > self._weapon_cooldown_seconds:
                    self._weapon_cooldown[key] = now
                    alert_fired = True

                    weapon_event = {
                        "event_type": event_type,
                        "object_type": class_name,
                        "severity": severity,
                        "confidence": round(confidence, 3),
                        "bbox": bbox,
                        "zone_id": zone_id if in_zone else None,
                        "zone_name": zone_name if in_zone else "",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    baseline_signals = {
                        "weapon_detected": True,
                        "weapon_in_zone": bool(in_zone),
                        "intrusion": False,
                        "loitering": False,
                        "crowd": False,
                    }
                    baseline_score = self._compute_threat(baseline_signals)
                    baseline_level = self._get_threat_level(baseline_score)
                    self._attach_threat_context(
                        weapon_event,
                        baseline_score,
                        baseline_level,
                        baseline_signals,
                    )
                    behavior_events.append(weapon_event)

                    self._publish_event(Event(
                        type=(
                            "WeaponInZoneDetected"
                            if in_zone
                            else "WeaponDetected"
                        ),
                        data=weapon_event,
                    ))

                    if pending_alerts is not None:
                        pending_alerts.append({
                            "event_type": event_type,
                            "track_id": None,
                            "zone": zone_name if in_zone else "",
                            "metadata": weapon_event,
                        })
                    elif self._alert_service is not None:
                        self._enqueue_alert(
                            event_type=event_type,
                            track_id=None,
                            zone=zone_name if in_zone else "",
                            metadata=weapon_event,
                            frame=frame.copy(),
                        )

                    logger.warning(
                        "WEAPON ALERT: type=%s class=%s confidence=%.2f "
                        "zone=%s consecutive=%d key=%s",
                        event_type,
                        class_name,
                        confidence,
                        zone_name if zone_name else "outside",
                        state["count"],
                        key,
                    )

        # Reset counters for weapon keys NOT seen this frame
        stale_keys = set(self._weapon_state.keys()) - seen_keys
        for k in stale_keys:
            self._weapon_state[k]["count"] = 0

        # Update active weapon alerts snapshot for drawing
        self._active_weapon_alerts = [
            s for s in self._weapon_state.values()
            if s["count"] >= self._weapon_consecutive_threshold
        ]

        # Clean up stale entries that have been zero for a while
        self._weapon_state = {
            k: v for k, v in self._weapon_state.items() if v["count"] > 0
        }

        return alert_fired

    def _draw_weapon_overlays(
        self,
        frame: np.ndarray,
    ) -> np.ndarray:
        """
        Draw weapon detection bounding boxes and alert text on the frame.

        Draws a red bounding box around each detected weapon along with
        a class label and confidence score. Also renders a prominent
        "WEAPON DETECTED" banner at the top of the frame.

        Args:
            frame: Annotated frame (will be modified in-place).

        Returns:
            np.ndarray: Frame with weapon overlays drawn.
        """
        if not self._active_weapon_alerts:
            return frame

        # Draw "WEAPON DETECTED" banner
        h, w = frame.shape[:2]
        has_critical = any(a.get("event_type") == "weapon_in_zone" for a in self._active_weapon_alerts)
        banner_colour = (0, 0, 180) if has_critical else (182, 89, 155)
        banner_text = "!! WEAPON IN ZONE !!" if has_critical else "!! WEAPON DETECTED !!"
        cv2.rectangle(frame, (0, h - 45), (w, h), banner_colour, -1)
        cv2.putText(
            frame,
            banner_text,
            (w // 2 - 160, h - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2,
        )

        for alert in self._active_weapon_alerts:
            bbox = alert["bbox"]
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            class_name = alert["class_name"]
            confidence = alert["confidence"]
            event_type = alert.get("event_type", "weapon_detected")
            zone_name = alert.get("zone_name", "")
            is_critical = event_type == "weapon_in_zone"
            box_colour = (0, 0, 255) if is_critical else (182, 89, 155)

            # Highlight critical weapon-in-zone with red and warning weapon with purple.
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_colour, 3)

            # Two-line label: "WEAPON" header + "Knife (0.87)" detail
            line1 = "CRITICAL WEAPON" if is_critical else "WEAPON WARNING"
            line2 = f"{class_name.capitalize()} ({confidence:.2f})"
            if zone_name:
                line2 = f"{line2} @ {zone_name}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw1, th1), _ = cv2.getTextSize(line1, font, 0.7, 2)
            (tw2, th2), _ = cv2.getTextSize(line2, font, 0.55, 1)
            label_w = max(tw1, tw2) + 12
            label_h = th1 + th2 + 20

            # Label background
            cv2.rectangle(
                frame, (x1, y1 - label_h), (x1 + label_w, y1), box_colour, -1,
            )
            # Line 1: "WEAPON" (bold white)
            cv2.putText(
                frame, line1, (x1 + 4, y1 - th2 - 14),
                font, 0.7, (255, 255, 255), 2,
            )
            # Line 2: "Knife (0.87)" (lighter white)
            cv2.putText(
                frame, line2, (x1 + 4, y1 - 5),
                font, 0.55, (255, 220, 220), 1,
            )

        return frame

    @staticmethod
    def _bbox_iou(
        box_a: list[float],
        box_b: list[float],
    ) -> float:
        """Compute IoU between two [x1, y1, x2, y2] boxes."""
        xa = max(box_a[0], box_b[0])
        ya = max(box_a[1], box_b[1])
        xb = min(box_a[2], box_b[2])
        yb = min(box_a[3], box_b[3])

        inter = max(0.0, xb - xa) * max(0.0, yb - ya)
        if inter == 0:
            return 0.0

        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        return inter / (area_a + area_b - inter)

    @property
    def is_running(self) -> bool:
        """Return whether the behavior worker is active."""
        return self._is_running

    @property
    def analyze_count(self) -> int:
        """Return the number of frames analyzed."""
        return self._analyze_count

    @property
    def stats(self) -> dict:
        """Return behavior worker statistics."""
        return {
            "is_running": self._is_running,
            "frames_analyzed": self._analyze_count,
            "avg_behavior_ms": round(self._avg_behavior_ms, 1),
            "avg_input_age_ms": round(self._avg_input_age_ms, 1),
            "frames_dropped": self._drop_count,
            "face_queue_depth": self._face_queue.qsize(),
            "pending_face_tracks": len(self._pending_tracks),
            "active_event_states": len(self._event_states),
            "alert_queue_depth": self._alert_queue.qsize(),
            "alerts_persisted": self._alert_persist_count,
            "alerts_dropped": self._alert_drop_count,
        }
