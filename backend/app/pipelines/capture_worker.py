"""
OVERWATCH — Capture Worker
=============================
Background worker that reads frames from the video source
and places them into the frame queue for downstream processing.

Supports multiple video source types (camera, demo, upload) through
the SourceManager abstraction.

Designed to run in a dedicated thread to avoid blocking
the asyncio event loop with OpenCV I/O operations.

Architecture:
    SourceManager.read() → FramePacket → frame_queue
"""

import logging
import queue
import threading
import time
from typing import Optional

from app.config import Settings
from app.core.queues import PipelineQueues, FramePacket
from app.services.source_manager import SourceManager
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)


class CaptureWorker:
    """
    Reads video frames in a background thread and feeds them
    into the pipeline's frame queue.

    Supports multiple source types through SourceManager.
    Handles frame skipping based on configuration to reduce
    processing load on CPU-constrained systems.

    Attributes:
        _settings: Application configuration.
        _video_service: Video capture service instance (backward compat).
        _source_manager: Unified source abstraction for frame reading.
        _queues: Pipeline queues for inter-worker communication.
        _behavior_worker: Optional reference for state reset on source change.
        _thread: Background thread handle.
        _is_running: Whether the worker is actively capturing.
        _frame_count: Total frames read.
    """

    def __init__(
        self,
        settings: Settings,
        video_service: VideoService,
        queues: PipelineQueues,
        behavior_worker: Optional[object] = None,
    ) -> None:
        """
        Initialize the CaptureWorker.

        Args:
            settings: Application configuration.
            video_service: Service for reading video frames (legacy).
            queues: Pipeline queues container.
            behavior_worker: Optional reference to behavior worker for
                           state reset on source switching.
        """
        self._settings: Settings = settings
        self._video_service: VideoService = video_service
        self._queues: PipelineQueues = queues
        self._behavior_worker: Optional[object] = behavior_worker
        self._source_manager: SourceManager = SourceManager()
        self._thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._frame_count: int = 0
        self._drop_count: int = 0
        self._avg_capture_ms: float = 0.0

    def start(self) -> None:
        """
        Start the capture worker in a background thread.

        Initializes the default camera source and runs the _capture_loop
        continuously until stop() is called.
        """
        if self._is_running:
            logger.warning("CaptureWorker already running")
            return

        # Initialize default camera source
        if not self._source_manager.set_source("camera"):
            logger.error("Failed to initialize default camera source")
            return

        self._is_running = True
        self._frame_count = 0
        self._drop_count = 0
        self._avg_capture_ms = 0.0
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="CaptureWorker",
            daemon=True,
        )
        self._thread.start()
        logger.info("CaptureWorker started with camera source")

    def stop(self) -> None:
        """
        Stop the capture worker and wait for the thread to finish.

        Releases the current source and blocks until the background
        thread exits.
        """
        self._is_running = False
        self._source_manager.release()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("CaptureWorker stopped (captured %d frames)", self._frame_count)

    def _capture_loop(self) -> None:
        """
        Main capture loop running in a background thread.

        Reads frames from SourceManager, applies frame skipping,
        wraps frames in FramePackets, and enqueues them. Drops frames
        if the queue is full to prevent backpressure.
        """
        skip_count = self._settings.pipeline_skip_frames
        frame_index = 0

        logger.info("Capture loop started (skip_frames=%d)", skip_count)

        while self._is_running:
            try:
                start_time = time.monotonic()
                ret, frame = self._source_manager.read()
                capture_time_ms = (time.monotonic() - start_time) * 1000

                if not ret or frame is None:
                    time.sleep(0.01)
                    continue

                alpha = 0.1
                if self._frame_count == 0:
                    self._avg_capture_ms = capture_time_ms
                else:
                    self._avg_capture_ms = (
                        alpha * capture_time_ms + (1 - alpha) * self._avg_capture_ms
                    )

                frame_index += 1

                # Frame skipping: only process every (skip_count)th frame
                if skip_count > 1 and (frame_index % skip_count) != 0:
                    continue

                packet = FramePacket(
                    frame=frame,
                    frame_index=frame_index,
                    timestamp_ns=time.monotonic_ns(),
                    capture_time_ms=round(capture_time_ms, 1),
                )

                try:
                    self._queues.frame_queue.put_nowait(packet)
                    self._frame_count += 1
                except queue.Full:
                    self._drop_count += 1
                    try:
                        self._queues.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queues.frame_queue.put_nowait(packet)
                    self._frame_count += 1
                    logger.debug("Frame queue full, replaced oldest with frame %d", frame_index)

            except Exception:
                logger.exception("Error in capture loop")
                time.sleep(0.1)

        logger.info("Capture loop exited")

    def switch_source(
        self, source_type: str, path: Optional[str] = None
    ) -> bool:
        """
        Switch to a different video source.

        Changes the active source and resets event state in the
        behavior worker to avoid stale detections from previous source.

        Args:
            source_type: One of "camera", "demo", or "upload".
            path: File path for demo/upload sources, None for camera.

        Returns:
            bool: True if source switch was successful.
        """
        try:
            if self._source_manager.set_source(source_type, path):
                logger.info(
                    "Source switched to %s (%s)",
                    source_type,
                    path or "default",
                )

                # Reset event state to prevent stale detections
                if self._behavior_worker is not None:
                    try:
                        if hasattr(self._behavior_worker, "reset_event_state"):
                            self._behavior_worker.reset_event_state()
                            logger.info("Event state reset after source switch")
                    except Exception as e:
                        logger.error("Error resetting event state: %s", e)

                return True
            else:
                logger.error("Failed to switch source to %s", source_type)
                return False

        except Exception as e:
            logger.error("Error switching source: %s", e)
            return False

    def set_behavior_worker(self, behavior_worker: object) -> None:
        """
        Set the behavior worker reference for state reset on source changes.

        Args:
            behavior_worker: Reference to the BehaviorWorker instance.
        """
        self._behavior_worker = behavior_worker

    def get_source_info(self) -> dict:
        """
        Get information about the current source.

        Returns:
            dict: Source information including type, path, and status.
        """
        info = self._source_manager.info
        info["is_capturing"] = self._is_running
        return info
    def is_running(self) -> bool:
        """Return whether the capture worker is active."""
        return self._is_running

    @property
    def frame_count(self) -> int:
        """Return the total number of frames captured."""
        return self._frame_count

    @property
    def stats(self) -> dict:
        """Return capture worker statistics."""
        return {
            "is_running": self._is_running,
            "frames_captured": self._frame_count,
            "frames_dropped": self._drop_count,
            "avg_capture_ms": round(self._avg_capture_ms, 1),
            "queue_depth": self._queues.frame_queue.qsize(),
        }
