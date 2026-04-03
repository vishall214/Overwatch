"""
OVERWATCH — Tracking Worker
================================
Background worker that pulls detection results from the
detection queue, runs ByteTrack object tracking to assign
persistent IDs, draws tracking labels, and pushes results
into the tracking queue.

Designed to run in a dedicated thread so tracking does not
block inference or the asyncio event loop.

Architecture:
    detection_queue → ByteTrack → tracking_queue → StreamWorker
"""

import logging
import queue
import threading
import time
from typing import Optional

import cv2
import numpy as np
import supervision as sv

from app.config import Settings
from app.core.queues import PipelineQueues, DetectionPacket, TrackingPacket
from app.models.tracking import TrackedObject, TrackState

logger = logging.getLogger(__name__)

# Bounding box drawing colours — one per track ID (cycling)
_COLOURS = [
    (0, 255, 0),
    (255, 0, 0),
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255),
    (128, 255, 0),
    (255, 128, 0),
    (0, 128, 255),
    (128, 0, 255),
]


class TrackingWorker:
    """
    Runs ByteTrack object tracking in a background thread.

    Reads DetectionPackets from the detection queue, updates
    the ByteTrack tracker with current detections, draws
    bounding boxes with track-ID labels on the frame, and
    enqueues TrackingPackets for the stream worker.

    Attributes:
        _settings: Application configuration.
        _queues: Pipeline queues for inter-worker communication.
        _tracker: Persistent ByteTrack tracker instance.
        _thread: Background thread handle.
        _is_running: Whether the worker is actively processing.
        _track_count: Total frames processed through tracking.
    """

    def __init__(
        self,
        settings: Settings,
        queues: PipelineQueues,
    ) -> None:
        self._settings: Settings = settings
        self._queues: PipelineQueues = queues
        self._tracker: sv.ByteTrack = sv.ByteTrack(
            track_activation_threshold=0.25,
            lost_track_buffer=30,
            minimum_matching_threshold=0.8,
            frame_rate=15,
        )
        self._thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._track_count: int = 0
        self._drop_count: int = 0
        self._avg_tracking_ms: float = 0.0
        self._avg_input_age_ms: float = 0.0

    def start(self) -> None:
        """Start the tracking worker in a background thread."""
        if self._is_running:
            logger.warning("TrackingWorker already running")
            return

        self._is_running = True
        self._track_count = 0
        self._drop_count = 0
        self._avg_tracking_ms = 0.0
        self._avg_input_age_ms = 0.0
        self._tracker.reset()
        self._thread = threading.Thread(
            target=self._tracking_loop,
            name="TrackingWorker",
            daemon=True,
        )
        self._thread.start()
        logger.info("TrackingWorker started")

    def stop(self) -> None:
        """Stop the tracking worker and wait for the thread to finish."""
        self._is_running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info(
            "TrackingWorker stopped (tracked %d frames)", self._track_count,
        )

    def _tracking_loop(self) -> None:
        """
        Main tracking loop running in a background thread.

        Pulls DetectionPackets from the detection queue, converts
        detections into supervision format, updates ByteTrack,
        draws annotated bounding boxes with track IDs, and pushes
        TrackingPackets to the tracking queue.
        """
        logger.info("Tracking loop started")

        while self._is_running:
            try:
                # Block with timeout to allow shutdown check
                try:
                    packet: DetectionPacket = self._queues.detection_queue.get(
                        timeout=0.1,
                    )
                except queue.Empty:
                    continue

                start_time = time.monotonic()
                input_age_ms = (time.monotonic_ns() - packet.timestamp_ns) / 1_000_000

                # --- Convert detections to supervision format -----------
                detections_list = packet.detections
                if detections_list:
                    xyxy = np.array(
                        [d["bbox"] for d in detections_list], dtype=np.float32,
                    )
                    confidence = np.array(
                        [d["confidence"] for d in detections_list], dtype=np.float32,
                    )
                    class_ids = np.array(
                        [d["class_id"] for d in detections_list], dtype=int,
                    )

                    sv_detections = sv.Detections(
                        xyxy=xyxy,
                        confidence=confidence,
                        class_id=class_ids,
                    )

                    # --- Update tracker (persists across frames) --------
                    tracked = self._tracker.update_with_detections(sv_detections)

                    # --- Build TrackedObject list and annotated frame ---
                    class_name_map = {
                        d["class_id"]: d["class_name"] for d in detections_list
                    }

                    tracked_objects: list[TrackedObject] = []
                    for i in range(len(tracked)):
                        track_id = int(tracked.tracker_id[i])
                        bbox = tracked.xyxy[i].tolist()
                        conf = float(tracked.confidence[i])
                        cls_id = int(tracked.class_id[i])
                        cls_name = class_name_map.get(cls_id, str(cls_id))

                        tracked_objects.append(TrackedObject(
                            track_id=track_id,
                            bbox=bbox,
                            confidence=conf,
                            class_id=cls_id,
                            class_name=cls_name,
                            state=TrackState.CONFIRMED,
                        ))
                else:
                    tracked_objects = []

                # --- Draw tracking labels on original frame -------------
                annotated = self._draw_tracking_labels(
                    packet.frame, tracked_objects,
                )

                tracked_dicts = [t.to_dict() for t in tracked_objects]
                tracking_time_ms = (time.monotonic() - start_time) * 1000
                self._track_count += 1
                alpha = 0.1
                if self._track_count == 1:
                    self._avg_tracking_ms = tracking_time_ms
                    self._avg_input_age_ms = input_age_ms
                else:
                    self._avg_tracking_ms = (
                        alpha * tracking_time_ms + (1 - alpha) * self._avg_tracking_ms
                    )
                    self._avg_input_age_ms = (
                        alpha * input_age_ms + (1 - alpha) * self._avg_input_age_ms
                    )

                tracking_packet = TrackingPacket(
                    frame=packet.frame,
                    annotated_frame=annotated,
                    tracked_objects=tracked_dicts,
                    frame_index=packet.frame_index,
                    timestamp_ns=packet.timestamp_ns,
                    capture_time_ms=packet.capture_time_ms,
                    inference_time_ms=packet.inference_time_ms,
                    tracking_time_ms=round(tracking_time_ms, 1),
                    weapon_detections=packet.weapon_detections,
                )

                try:
                    self._queues.tracking_queue.put_nowait(tracking_packet)
                except queue.Full:
                    self._drop_count += 1
                    try:
                        self._queues.tracking_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queues.tracking_queue.put_nowait(tracking_packet)
                    logger.debug(
                        "Tracking queue full, replaced oldest with frame %d",
                        packet.frame_index,
                    )

                if self._track_count % 30 == 0:
                    logger.info(
                        "perf tracking frame=%d input_age_ms=%.1f tracking_time_ms=%.1f tracking_queue=%d",
                        packet.frame_index,
                        input_age_ms,
                        tracking_time_ms,
                        self._queues.tracking_queue.qsize(),
                    )

            except Exception:
                logger.exception("Error in tracking loop")
                time.sleep(0.1)

        logger.info("Tracking loop exited")

    @staticmethod
    def _draw_tracking_labels(
        frame: np.ndarray,
        tracked_objects: list[TrackedObject],
    ) -> np.ndarray:
        """
        Draw bounding boxes with tracking labels on a frame.

        Labels use the format: "{class_name} #{track_id}"

        Args:
            frame: Original BGR frame (will be copied).
            tracked_objects: List of TrackedObject instances.

        Returns:
            np.ndarray: Annotated frame with tracking boxes.
        """
        annotated = frame.copy()
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2

        for obj in tracked_objects:
            x1, y1, x2, y2 = (
                int(obj.bbox[0]),
                int(obj.bbox[1]),
                int(obj.bbox[2]),
                int(obj.bbox[3]),
            )
            colour = _COLOURS[obj.track_id % len(_COLOURS)]
            label = f"{obj.class_name} #{obj.track_id}"

            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), colour, thickness)

            # Draw label background
            (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)
            cv2.rectangle(
                annotated, (x1, y1 - th - 8), (x1 + tw + 4, y1), colour, -1,
            )
            # Draw label text
            cv2.putText(
                annotated, label, (x1 + 2, y1 - 4),
                font, font_scale, (0, 0, 0), thickness,
            )

        return annotated

    @property
    def is_running(self) -> bool:
        """Return whether the tracking worker is active."""
        return self._is_running

    @property
    def track_count(self) -> int:
        """Return the number of frames tracked."""
        return self._track_count

    @property
    def stats(self) -> dict:
        """Return tracking worker statistics."""
        return {
            "is_running": self._is_running,
            "frames_tracked": self._track_count,
            "avg_tracking_ms": round(self._avg_tracking_ms, 1),
            "avg_input_age_ms": round(self._avg_input_age_ms, 1),
            "frames_dropped": self._drop_count,
        }
