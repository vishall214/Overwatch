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
from app.utils.geometry_utils import point_in_polygon, bbox_center

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
    ) -> None:
        self._settings: Settings = settings
        self._queues: PipelineQueues = queues
        self._event_bus: EventBus = event_bus
        self._alert_service: Optional[AlertService] = alert_service
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
        self._thread = threading.Thread(
            target=self._behavior_loop,
            name="BehaviorWorker",
            daemon=True,
        )
        self._thread.start()
        logger.info("BehaviorWorker started")

    def stop(self) -> None:
        """Stop the behavior worker and wait for the thread to finish."""
        self._is_running = False
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

                behavior_events: list[dict] = []
                intrusion_detected = False
                loitering_detected = False
                crowd_detected = False
                people_in_zone = 0
                loiter_timers: dict[int, float] = {}
                now = time.monotonic()
                current_track_ids: set[int] = set()

                # --- Check each tracked object against Zone A ----------
                for obj in packet.tracked_objects:
                    bbox = obj["bbox"]
                    center = bbox_center(bbox)
                    track_id = obj["track_id"]
                    current_track_ids.add(track_id)

                    if point_in_polygon(center, self._zone_polygon):
                        # Count persons inside zone for crowd detection
                        if obj.get("class_name", "unknown") == "person":
                            people_in_zone += 1
                        intrusion_detected = True

                        # Intrusion: publish on first entry
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
                            self._publish_event(Event(
                                type="IntrusionDetected",
                                data=event_data,
                            ))
                            if self._alert_service is not None:
                                self._alert_service.create_alert(
                                    event_type="intrusion",
                                    track_id=track_id,
                                    zone="A",
                                    metadata=event_data,
                                    frame=packet.frame,
                                )
                            logger.warning(
                                "INTRUSION: %s #%d entered Zone A",
                                obj.get("class_name", "unknown"),
                                track_id,
                            )

                        # Loitering: track time inside zone
                        if track_id not in self._loiter_state:
                            self._loiter_state[track_id] = now

                        duration = now - self._loiter_state[track_id]
                        loiter_timers[track_id] = duration

                        if duration >= self._loiter_threshold:
                            loitering_detected = True
                            if track_id not in self._loiter_alerted:
                                self._loiter_alerted.add(track_id)
                                loiter_event = {
                                    "track_id": track_id,
                                    "duration": round(duration, 1),
                                    "zone": "A",
                                    "class_name": obj.get("class_name", "unknown"),
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                                behavior_events.append(loiter_event)
                                self._publish_event(Event(
                                    type="LoiteringDetected",
                                    data=loiter_event,
                                ))
                                if self._alert_service is not None:
                                    self._alert_service.create_alert(
                                        event_type="loitering",
                                        track_id=track_id,
                                        zone="A",
                                        metadata=loiter_event,
                                        frame=packet.frame,
                                    )
                                logger.warning(
                                    "LOITERING: %s #%d in Zone A for %.1fs",
                                    obj.get("class_name", "unknown"),
                                    track_id,
                                    duration,
                                )
                    else:
                        # Object left the zone
                        self._active_intrusions.discard(track_id)
                        self._loiter_state.pop(track_id, None)
                        self._loiter_alerted.discard(track_id)

                # --- Crowd detection -----------------------------------
                if people_in_zone > self._crowd_threshold:
                    crowd_detected = True
                    if not self._crowd_alerted:
                        self._crowd_alerted = True
                        crowd_event = {
                            "count": people_in_zone,
                            "threshold": self._crowd_threshold,
                            "zone": "A",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        behavior_events.append(crowd_event)
                        self._publish_event(Event(
                            type="CrowdDetected",
                            data=crowd_event,
                        ))
                        if self._alert_service is not None:
                            self._alert_service.create_alert(
                                event_type="crowd",
                                track_id=None,
                                zone="A",
                                metadata=crowd_event,
                                frame=packet.frame,
                            )
                        logger.warning(
                            "CROWD: %d persons in Zone A (threshold %d)",
                            people_in_zone, self._crowd_threshold,
                        )
                else:
                    self._crowd_alerted = False

                # Clean up state for tracks that disappeared
                stale_ids = set(self._loiter_state.keys()) - current_track_ids
                for tid in stale_ids:
                    self._loiter_state.pop(tid, None)
                    self._loiter_alerted.discard(tid)
                    self._active_intrusions.discard(tid)

                # --- Draw zone overlay and alerts ---------------------
                annotated = self._draw_zone_overlay(
                    packet.annotated_frame,
                    intrusion_detected,
                    loitering_detected,
                    crowd_detected,
                    people_in_zone,
                    loiter_timers,
                )

                behavior_packet = BehaviorPacket(
                    frame=packet.frame,
                    annotated_frame=annotated,
                    tracked_objects=packet.tracked_objects,
                    behavior_events=behavior_events,
                    frame_index=packet.frame_index,
                    timestamp_ns=packet.timestamp_ns,
                )

                try:
                    self._queues.behavior_queue.put_nowait(behavior_packet)
                    self._analyze_count += 1
                except queue.Full:
                    logger.debug(
                        "Behavior queue full, dropping result for frame %d",
                        packet.frame_index,
                    )

            except Exception:
                logger.exception("Error in behavior loop")
                time.sleep(0.1)

        logger.info("Behavior loop exited")

    def _draw_zone_overlay(
        self,
        frame: np.ndarray,
        intrusion_detected: bool,
        loitering_detected: bool,
        crowd_detected: bool,
        people_in_zone: int,
        loiter_timers: dict[int, float],
    ) -> np.ndarray:
        """
        Draw the intrusion zone polygon, loiter timers, crowd count, and alert text.

        Args:
            frame: Annotated frame (will be copied).
            intrusion_detected: Whether any object is inside Zone A.
            loitering_detected: Whether any object exceeded loiter threshold.
            crowd_detected: Whether crowd threshold was exceeded.
            people_in_zone: Number of persons currently inside the zone.
            loiter_timers: Maps track_id → seconds inside zone.

        Returns:
            np.ndarray: Frame with zone overlay drawn.
        """
        annotated = frame.copy()

        # Draw zone polygon
        pts = np.array(self._zone_polygon, dtype=np.int32).reshape((-1, 1, 2))
        zone_colour = (0, 0, 255) if intrusion_detected else (0, 255, 0)

        # Semi-transparent fill
        overlay = annotated.copy()
        cv2.fillPoly(overlay, [pts], zone_colour)
        cv2.addWeighted(overlay, 0.2, annotated, 0.8, 0, annotated)

        # Zone border
        cv2.polylines(annotated, [pts], isClosed=True, color=zone_colour, thickness=2)

        # Zone label
        cv2.putText(
            annotated, "Zone A", (int(self._zone_polygon[0][0]) + 5, int(self._zone_polygon[0][1]) - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, zone_colour, 1,
        )

        # Intrusion alert
        y_offset = 30
        if intrusion_detected:
            cv2.putText(
                annotated, "INTRUSION DETECTED", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2,
            )
            y_offset += 35

        # Loitering alert
        if loitering_detected:
            cv2.putText(
                annotated, "LOITERING DETECTED", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2,
            )
            y_offset += 35

        # Crowd count overlay
        cv2.putText(
            annotated, f"People Count: {people_in_zone}", (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2,
        )
        y_offset += 30

        # Crowd alert
        if crowd_detected:
            cv2.putText(
                annotated, "CROWD DETECTED", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2,
            )
            y_offset += 35

        # Per-object loiter timers
        for track_id, duration in loiter_timers.items():
            timer_text = f"LOITERING TIMER #{track_id}: {duration:.1f}s"
            cv2.putText(
                annotated, timer_text, (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2,
            )
            y_offset += 25

        return annotated

    @property
    def is_running(self) -> bool:
        """Return whether the behavior worker is active."""
        return self._is_running

    @property
    def analyze_count(self) -> int:
        """Return the number of frames analyzed."""
        return self._analyze_count
