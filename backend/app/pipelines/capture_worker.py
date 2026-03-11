"""
OVERWATCH — Capture Worker
=============================
Background worker that reads frames from the video source
and places them into the frame queue for downstream processing.

Designed to run in a dedicated thread to avoid blocking
the asyncio event loop with OpenCV I/O operations.

Architecture:
    VideoService.read_frame() → FramePacket → frame_queue
"""

import logging
import queue
import threading
import time
from typing import Optional

from app.config import Settings
from app.core.queues import PipelineQueues, FramePacket
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)


class CaptureWorker:
    """
    Reads video frames in a background thread and feeds them
    into the pipeline's frame queue.

    Handles frame skipping based on configuration to reduce
    processing load on CPU-constrained systems.

    Attributes:
        _settings: Application configuration.
        _video_service: Video capture service instance.
        _queues: Pipeline queues for inter-worker communication.
        _thread: Background thread handle.
        _is_running: Whether the worker is actively capturing.
        _frame_count: Total frames read.
    """

    def __init__(
        self,
        settings: Settings,
        video_service: VideoService,
        queues: PipelineQueues,
    ) -> None:
        """
        Initialize the CaptureWorker.

        Args:
            settings: Application configuration.
            video_service: Service for reading video frames.
            queues: Pipeline queues container.
        """
        self._settings: Settings = settings
        self._video_service: VideoService = video_service
        self._queues: PipelineQueues = queues
        self._thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._frame_count: int = 0
        self._drop_count: int = 0
        self._avg_capture_ms: float = 0.0

    def start(self) -> None:
        """
        Start the capture worker in a background thread.

        The thread runs the _capture_loop method continuously
        until stop() is called.
        """
        if self._is_running:
            logger.warning("CaptureWorker already running")
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
        logger.info("CaptureWorker started")

    def stop(self) -> None:
        """
        Stop the capture worker and wait for the thread to finish.

        Blocks until the background thread exits.
        """
        self._is_running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("CaptureWorker stopped (captured %d frames)", self._frame_count)

    def _capture_loop(self) -> None:
        """
        Main capture loop running in a background thread.

        Reads frames from the video source, applies frame skipping,
        wraps frames in FramePackets, and enqueues them. Drops frames
        if the queue is full to prevent backpressure.
        """
        skip_count = self._settings.pipeline_skip_frames
        frame_index = 0

        logger.info("Capture loop started (skip_frames=%d)", skip_count)

        while self._is_running:
            try:
                start_time = time.monotonic()
                frame = self._video_service.read_frame()
                capture_time_ms = (time.monotonic() - start_time) * 1000

                if frame is None:
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

    @property
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
