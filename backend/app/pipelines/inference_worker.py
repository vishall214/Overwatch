"""
OVERWATCH — Inference Worker
================================
Background worker that pulls frames from the frame queue,
runs YOLOv8 detection, publishes DetectionEvents to the
event bus, and places results into the detection queue.

Designed to run in a dedicated thread to avoid blocking
the asyncio event loop with model inference.

Architecture:
    frame_queue → DetectionService.detect()
               → EventBus.publish(DetectionEvent)
               → DetectionPacket → detection_queue
"""

import asyncio
import logging
import queue
import threading
import time
from typing import Optional

from app.config import Settings
from app.core.event_bus import EventBus, Event
from app.core.queues import PipelineQueues, FramePacket, DetectionPacket
from app.services.detection_service import DetectionService
from app.services.module_controller import ModuleController

logger = logging.getLogger(__name__)


class InferenceWorker:
    """
    Runs object detection inference in a background thread.

    Reads FramePackets from the frame queue, executes YOLOv8
    detection, publishes a DetectionEvent to the event bus,
    and enqueues DetectionPackets for downstream consumers.

    Attributes:
        _settings: Application configuration.
        _detection_service: YOLOv8 detection service.
        _queues: Pipeline queues for inter-worker communication.
        _event_bus: Event bus for publishing detection events.
        _thread: Background thread handle.
        _is_running: Whether the worker is actively processing.
        _inference_count: Total frames processed through inference.
        _avg_inference_ms: Rolling average inference time in milliseconds.
    """

    def __init__(
        self,
        settings: Settings,
        detection_service: DetectionService,
        queues: PipelineQueues,
        event_bus: EventBus,
        module_controller: Optional[ModuleController] = None,
    ) -> None:
        """
        Initialize the InferenceWorker.

        Args:
            settings: Application configuration.
            detection_service: YOLOv8 detection service.
            queues: Pipeline queues container.
            event_bus: Event bus for publishing detection events.
            module_controller: Optional analytics module state controller.
        """
        self._settings: Settings = settings
        self._detection_service: DetectionService = detection_service
        self._queues: PipelineQueues = queues
        self._event_bus: EventBus = event_bus
        self._module_controller: Optional[ModuleController] = module_controller
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._inference_count: int = 0
        self._avg_inference_ms: float = 0.0
        self._frame_skip_counter: int = 0
        # Keep inference skipping configurable; default is 1 (no extra skipping).
        self._skip_frames: int = max(1, int(settings.inference_skip_frames))
        self._drop_count: int = 0
        self._avg_input_age_ms: float = 0.0
        self._weapon_skip_frames: int = max(1, int(settings.weapon_skip_frames))

    def start(self) -> None:
        """
        Start the inference worker in a background thread.

        The detection model must be loaded before calling start.
        """
        if self._is_running:
            logger.warning("InferenceWorker already running")
            return

        if not self._detection_service.is_loaded:
            logger.error("Cannot start InferenceWorker: detection model not loaded")
            return

        # Capture the running asyncio loop for thread-safe event publishing
        try:
            self._event_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._event_loop = None

        self._is_running = True
        self._inference_count = 0
        self._avg_inference_ms = 0.0
        self._frame_skip_counter = 0
        self._drop_count = 0
        self._avg_input_age_ms = 0.0
        self._thread = threading.Thread(
            target=self._inference_loop,
            name="InferenceWorker",
            daemon=True,
        )
        self._thread.start()
        logger.info("InferenceWorker started")

    def stop(self) -> None:
        """
        Stop the inference worker and wait for the thread to finish.

        Blocks until the background thread exits.
        """
        self._is_running = False
        if self._thread is not None:
            self._thread.join(timeout=10.0)
            self._thread = None
        logger.info(
            "InferenceWorker stopped (processed %d frames, avg %.1f ms/frame)",
            self._inference_count,
            self._avg_inference_ms,
        )

    def _publish_event(self, event: Event) -> None:
        """
        Publish an event to the bus from a worker thread.

        Uses asyncio.run_coroutine_threadsafe when an event loop
        is available, otherwise logs a warning.

        Args:
            event: The Event instance to publish.
        """
        if self._event_loop is not None and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._event_bus.publish(event),
                self._event_loop,
            )
        else:
            logger.debug("No event loop available, skipping event publish")

    def _inference_loop(self) -> None:
        """
        Main inference loop running in a background thread.

        Pulls FramePackets from the frame queue, runs detection,
        publishes a DetectionEvent to the event bus, and pushes
        DetectionPackets to the detection queue.
        Uses a short timeout to allow clean shutdown.
        """
        logger.info("Inference loop started")

        while self._is_running:
            try:
                # Block with timeout to allow shutdown check
                try:
                    packet: FramePacket = self._queues.frame_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Keep skip counter for observability; processing is no longer skipped.
                self._frame_skip_counter += 1

                input_age_ms = (time.monotonic_ns() - packet.timestamp_ns) / 1_000_000

                # Run detection
                start_time = time.monotonic()
                result = self._detection_service.detect(packet.frame)

                # Weapon detection runs on a configurable cadence to limit overhead.
                weapon_detections_list = None
                weapon_enabled = (
                    self._module_controller.is_enabled("weapon_detection")
                    if self._module_controller is not None
                    else True
                )
                if (
                    weapon_enabled
                    and
                    self._detection_service.weapon_is_loaded
                    and packet.frame_index % self._weapon_skip_frames == 0
                ):
                    weapon_results = self._detection_service.detect_weapons(packet.frame)
                    weapon_detections_list = [d.to_dict() for d in weapon_results]
                    if weapon_detections_list:
                        logger.info(
                            "weapon candidates frame=%d count=%d labels=%s",
                            packet.frame_index,
                            len(weapon_detections_list),
                            [w.get("class_name", "unknown") for w in weapon_detections_list],
                        )

                inference_ms = (time.monotonic() - start_time) * 1000

                # Update rolling average
                self._inference_count += 1
                alpha = 0.1  # Exponential moving average factor
                if self._inference_count == 1:
                    self._avg_inference_ms = inference_ms
                    self._avg_input_age_ms = input_age_ms
                else:
                    self._avg_inference_ms = (
                        alpha * inference_ms + (1 - alpha) * self._avg_inference_ms
                    )
                    self._avg_input_age_ms = (
                        alpha * input_age_ms + (1 - alpha) * self._avg_input_age_ms
                    )

                # Log detections only when debug flag is enabled
                if self._settings.debug_detection_logs:
                    for d in result.detections:
                        logger.debug("Detected: %s (%.2f)", d.class_name, d.confidence)

                # Serialize detections for the packet
                detection_dicts = [d.to_dict() for d in result.detections]

                # Publish DetectionEvent to event bus
                self._publish_event(Event(
                    type="DetectionComplete",
                    data={
                        "frame_index": packet.frame_index,
                        "detection_count": len(result.detections),
                        "detections": detection_dicts,
                        "inference_ms": round(inference_ms, 1),
                        "weapon_count": (
                            len(weapon_detections_list)
                            if weapon_detections_list is not None
                            else 0
                        ),
                    },
                ))

                # Build detection packet for downstream workers
                detection_packet = DetectionPacket(
                    frame=packet.frame,
                    annotated_frame=result.annotated_frame,
                    detections=detection_dicts,
                    frame_index=packet.frame_index,
                    timestamp_ns=packet.timestamp_ns,
                    capture_time_ms=packet.capture_time_ms,
                    inference_time_ms=round(inference_ms, 1),
                    weapon_detections=weapon_detections_list,
                )

                try:
                    self._queues.detection_queue.put_nowait(detection_packet)
                except queue.Full:
                    self._drop_count += 1
                    try:
                        self._queues.detection_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queues.detection_queue.put_nowait(detection_packet)
                    logger.debug(
                        "Detection queue full, replaced oldest with frame %d",
                        packet.frame_index,
                    )

                if self._inference_count % 30 == 0:
                    logger.info(
                        "perf inference frame=%d capture_time_ms=%.1f input_age_ms=%.1f inference_time_ms=%.1f detection_queue=%d",
                        packet.frame_index,
                        packet.capture_time_ms,
                        input_age_ms,
                        inference_ms,
                        self._queues.detection_queue.qsize(),
                    )

            except Exception:
                logger.exception("Error in inference loop")
                time.sleep(0.1)

        logger.info("Inference loop exited")

    @property
    def is_running(self) -> bool:
        """Return whether the inference worker is active."""
        return self._is_running

    @property
    def stats(self) -> dict:
        """
        Return inference worker statistics.

        Returns:
            dict: Worker stats including count and timing.
        """
        return {
            "is_running": self._is_running,
            "frames_processed": self._inference_count,
            "avg_inference_ms": round(self._avg_inference_ms, 1),
            "avg_input_age_ms": round(self._avg_input_age_ms, 1),
            "frames_dropped": self._drop_count,
            "skip_frames": self._skip_frames,
        }
