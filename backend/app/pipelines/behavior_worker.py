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
from typing import Optional

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
        self._loiter_state: dict[int, float] = {}
        self._loiter_alerted: set[int] = set()
        self._crowd_alerted: bool = False
        self._crowd_alerted_zones: set[int] = set()
        self._face_match_alerted: set[int] = set()
        self._identity_cache: dict[int, dict] = {}
        self._pending_tracks: set[int] = set()
        self._face_queue: queue.Queue = queue.Queue(maxsize=32)
        self._face_thread: Optional[threading.Thread] = None
        self._drop_count: int = 0
        self._avg_behavior_ms: float = 0.0
        self._avg_input_age_ms: float = 0.0

    def start(self) -> None:
        """Start the behavior worker in a background thread."""
        if self._is_running:
            logger.warning("BehaviorWorker already running")
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
        self._crowd_alerted = False
        self._crowd_alerted_zones.clear()
        self._face_match_alerted.clear()
        self._identity_cache.clear()
        self._pending_tracks.clear()
        self._drop_count = 0
        self._avg_behavior_ms = 0.0
        self._avg_input_age_ms = 0.0
        # Drain any stale items from the face queue
        while not self._face_queue.empty():
            try:
                self._face_queue.get_nowait()
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
        if self._face_thread is not None:
            self._face_thread.join(timeout=5.0)
            self._face_thread = None
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info(
            "BehaviorWorker stopped (analyzed %d frames)", self._analyze_count,
        )

    def _publish_event(self, event: Event) -> None:
        """Publish an event to the bus from a worker thread."""
        if self._event_loop is not None and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._event_bus.publish(event),
                self._event_loop,
            )
        else:
            logger.debug("No event loop available, skipping event publish")

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
                        self._publish_event(Event(
                            type="FaceMatchDetected",
                            data=match_event,
                        ))
                        if self._alert_service is not None:
                            self._alert_service.create_alert(
                                event_type="face_match",
                                track_id=track_id,
                                zone="",
                                metadata=match_event,
                                frame=frame,
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
                    else {"intrusion": True, "loitering": True, "crowd": True}
                )

                # --- Resolve zones (cached — no DB call) ---------------
                user_zones: list[dict] = []
                if self._zone_service is not None:
                    user_zones = self._zone_service.get_zones()
                use_legacy = len(user_zones) == 0

                frame_h, frame_w = packet.frame.shape[:2]

                # Per-zone counters for crowd detection
                people_per_zone: dict[int, int] = {}

                # --- Check each tracked object against zones ----------
                for obj in packet.tracked_objects:
                    bbox = obj["bbox"]
                    center = bbox_center(bbox)
                    track_id = obj["track_id"]
                    current_track_ids.add(track_id)
                    is_person = obj.get("class_name", "unknown") == "person"

                    in_any_zone = False

                    if use_legacy:
                        # ---------- Legacy polygon fallback ----------
                        if point_in_polygon(center, self._zone_polygon):
                            in_any_zone = True
                            if is_person:
                                people_in_zone += 1

                            if _mod["intrusion"]:
                                intrusion_detected = True
                                if track_id not in self._active_intrusions:
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
                                    if self._alert_service is not None:
                                        self._alert_service.create_alert(
                                            event_type="intrusion", track_id=track_id,
                                            zone="A", metadata=event_data, frame=packet.frame,
                                        )
                                    logger.warning("INTRUSION: %s #%d entered Zone A", obj.get("class_name", "unknown"), track_id)
                            else:
                                self._active_intrusions.discard(track_id)

                            if _mod["loitering"]:
                                if track_id not in self._loiter_state:
                                    self._loiter_state[track_id] = now
                                duration = now - self._loiter_state[track_id]
                                loiter_timers[track_id] = duration
                                if duration >= self._loiter_threshold:
                                    loitering_detected = True
                                    if track_id not in self._loiter_alerted:
                                        self._loiter_alerted.add(track_id)
                                        loiter_event = {
                                            "track_id": track_id, "duration": round(duration, 1),
                                            "zone": "A", "class_name": obj.get("class_name", "unknown"),
                                            "timestamp": datetime.now(timezone.utc).isoformat(),
                                        }
                                        behavior_events.append(loiter_event)
                                        self._publish_event(Event(type="LoiteringDetected", data=loiter_event))
                                        if self._alert_service is not None:
                                            self._alert_service.create_alert(
                                                event_type="loitering", track_id=track_id,
                                                zone="A", metadata=loiter_event, frame=packet.frame,
                                            )
                                        logger.warning("LOITERING: %s #%d in Zone A for %.1fs", obj.get("class_name", "unknown"), track_id, duration)
                            else:
                                self._loiter_state.pop(track_id, None)
                                self._loiter_alerted.discard(track_id)
                    else:
                        # ---------- User-defined rectangular zones ----------
                        for zone in user_zones:
                            if not rect_intersects_bbox(zone, bbox, frame_w, frame_h):
                                continue
                            in_any_zone = True
                            zone_name = zone.get("name", f"Zone {zone['id']}")
                            zone_type = zone["type"]
                            zone_id = zone["id"]

                            if is_person:
                                people_per_zone[zone_id] = people_per_zone.get(zone_id, 0) + 1

                            if zone_type == "intrusion" and _mod["intrusion"]:
                                intrusion_detected = True
                                intrusion_key = (track_id, zone_id)
                                if track_id not in self._active_intrusions:
                                    self._active_intrusions.add(track_id)
                                    event_data = {
                                        "track_id": track_id, "zone": zone_name,
                                        "class_name": obj.get("class_name", "unknown"),
                                        "bbox": bbox,
                                        "timestamp": datetime.now(timezone.utc).isoformat(),
                                    }
                                    behavior_events.append(event_data)
                                    self._publish_event(Event(type="IntrusionDetected", data=event_data))
                                    if self._alert_service is not None:
                                        self._alert_service.create_alert(
                                            event_type="intrusion", track_id=track_id,
                                            zone=zone_name, metadata=event_data, frame=packet.frame,
                                        )
                                    logger.warning("INTRUSION: %s #%d entered %s", obj.get("class_name", "unknown"), track_id, zone_name)

                            if zone_type == "loitering" and _mod["loitering"]:
                                if track_id not in self._loiter_state:
                                    self._loiter_state[track_id] = now
                                duration = now - self._loiter_state[track_id]
                                loiter_timers[track_id] = duration
                                if duration >= self._loiter_threshold:
                                    loitering_detected = True
                                    if track_id not in self._loiter_alerted:
                                        self._loiter_alerted.add(track_id)
                                        loiter_event = {
                                            "track_id": track_id, "duration": round(duration, 1),
                                            "zone": zone_name, "class_name": obj.get("class_name", "unknown"),
                                            "timestamp": datetime.now(timezone.utc).isoformat(),
                                        }
                                        behavior_events.append(loiter_event)
                                        self._publish_event(Event(type="LoiteringDetected", data=loiter_event))
                                        if self._alert_service is not None:
                                            self._alert_service.create_alert(
                                                event_type="loitering", track_id=track_id,
                                                zone=zone_name, metadata=loiter_event, frame=packet.frame,
                                            )
                                        logger.warning("LOITERING: %s #%d in %s for %.1fs", obj.get("class_name", "unknown"), track_id, zone_name, duration)

                    if not in_any_zone:
                        # Object left all zones
                        self._active_intrusions.discard(track_id)
                        self._loiter_state.pop(track_id, None)
                        self._loiter_alerted.discard(track_id)

                # --- Crowd detection -----------------------------------
                if use_legacy:
                    if _mod["crowd"] and people_in_zone > self._crowd_threshold:
                        crowd_detected = True
                        if not self._crowd_alerted:
                            self._crowd_alerted = True
                            crowd_event = {
                                "count": people_in_zone, "threshold": self._crowd_threshold,
                                "zone": "A", "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                            behavior_events.append(crowd_event)
                            self._publish_event(Event(type="CrowdDetected", data=crowd_event))
                            if self._alert_service is not None:
                                self._alert_service.create_alert(
                                    event_type="crowd", track_id=None,
                                    zone="A", metadata=crowd_event, frame=packet.frame,
                                )
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
                            if zid not in self._crowd_alerted_zones:
                                self._crowd_alerted_zones.add(zid)
                                crowd_event = {
                                    "count": z_count, "threshold": self._crowd_threshold,
                                    "zone": zone_name, "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                                behavior_events.append(crowd_event)
                                self._publish_event(Event(type="CrowdDetected", data=crowd_event))
                                if self._alert_service is not None:
                                    self._alert_service.create_alert(
                                        event_type="crowd", track_id=None,
                                        zone=zone_name, metadata=crowd_event, frame=packet.frame,
                                    )
                                logger.warning("CROWD: %d persons in %s (threshold %d)", z_count, zone_name, self._crowd_threshold)
                        else:
                            self._crowd_alerted_zones.discard(zid)

                # Clean up state for tracks that disappeared
                stale_ids = set(self._loiter_state.keys()) - current_track_ids
                for tid in stale_ids:
                    self._loiter_state.pop(tid, None)
                    self._loiter_alerted.discard(tid)
                    self._active_intrusions.discard(tid)

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

                # --- Draw zone overlay and alerts ---------------------
                annotated = self._draw_zone_overlay(
                    packet.annotated_frame,
                    intrusion_detected,
                    loitering_detected,
                    crowd_detected,
                    people_in_zone,
                    loiter_timers,
                    user_zones,
                )

                # --- Draw face identity overlays ----------------------
                annotated = self._draw_face_overlays(annotated, face_results)
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
                        "perf behavior frame=%d input_age_ms=%.1f behavior_time_ms=%.1f behavior_queue=%d face_queue=%d",
                        packet.frame_index,
                        input_age_ms,
                        behavior_time_ms,
                        self._queues.behavior_queue.qsize(),
                        self._face_queue.qsize(),
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
        }
