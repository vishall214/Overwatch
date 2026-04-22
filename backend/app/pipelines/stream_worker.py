"""
OVERWATCH — Stream Worker
============================
Background worker that pulls annotated frames from the
detection queue, encodes them as JPEG, and pushes the
encoded bytes into the stream queue for MJPEG delivery.

Designed to run in a dedicated thread so JPEG encoding
does not block inference or the asyncio event loop.

Architecture:
    behavior_queue → cv2.imencode → stream_queue → MJPEG endpoint
"""

import logging
import queue
import threading
import time
from typing import Optional

import cv2

from app.config import Settings
from app.core.queues import PipelineQueues, BehaviorPacket

logger = logging.getLogger(__name__)


class StreamWorker:
    """
    Encodes annotated frames as JPEG in a background thread.

    Reads BehaviorPackets from the behavior queue, encodes the
    annotated frame using OpenCV imencode, and pushes the resulting
    bytes into the stream queue for the MJPEG endpoint to consume.

    Attributes:
        _settings: Application configuration.
        _queues: Pipeline queues for inter-worker communication.
        _thread: Background thread handle.
        _is_running: Whether the worker is actively encoding.
        _encode_count: Total frames encoded.
    """

    def __init__(
        self,
        settings: Settings,
        queues: PipelineQueues,
    ) -> None:
        """
        Initialize the StreamWorker.

        Args:
            settings: Application configuration.
            queues: Pipeline queues container.
        """
        self._settings: Settings = settings
        self._queues: PipelineQueues = queues
        self._thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._encode_count: int = 0
        self._drop_count: int = 0
        self._avg_stream_ms: float = 0.0
        self._avg_total_latency_ms: float = 0.0

    def start(self) -> None:
        """
        Start the stream worker in a background thread.

        The thread runs the _encode_loop method continuously
        until stop() is called.
        """
        if self._is_running:
            logger.warning("StreamWorker already running")
            return

        if self._thread is not None and self._thread.is_alive():
            logger.warning("StreamWorker thread still alive; refusing duplicate start")
            return

        self._is_running = True
        self._encode_count = 0
        self._drop_count = 0
        self._avg_stream_ms = 0.0
        self._avg_total_latency_ms = 0.0
        self._thread = threading.Thread(
            target=self._encode_loop,
            name="StreamWorker",
            daemon=True,
        )
        self._thread.start()
        logger.info("StreamWorker started")

    def stop(self) -> None:
        """
        Stop the stream worker and wait for the thread to finish.

        Blocks until the background thread exits.
        """
        self._is_running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("StreamWorker thread did not stop within timeout")
            else:
                self._thread = None
        logger.info("StreamWorker stopped (encoded %d frames)", self._encode_count)

    def _encode_loop(self) -> None:
        """
        Main encoding loop running in a background thread.

        Pulls BehaviorPackets from the behavior queue, encodes the
        annotated frame as JPEG, and pushes the bytes into the stream
        queue.  Drops results if the stream queue is full to keep only
        the freshest frame available for viewers.
        """
        jpeg_quality = self._settings.stream_quality

        logger.info("Encode loop started (jpeg_quality=%d)", jpeg_quality)

        while self._is_running:
            try:
                # Block with timeout to allow shutdown check
                try:
                    packet: BehaviorPacket = self._queues.behavior_queue.get(
                        timeout=0.1,
                    )
                except queue.Empty:
                    continue

                # Encode the annotated frame as JPEG
                start_time = time.monotonic()
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
                success, buffer = cv2.imencode(".jpg", packet.annotated_frame, encode_params)
                stream_time_ms = (time.monotonic() - start_time) * 1000
                total_latency_ms = (time.monotonic_ns() - packet.timestamp_ns) / 1_000_000

                if not success:
                    logger.warning("Failed to encode frame %d as JPEG", packet.frame_index)
                    continue

                jpeg_bytes: bytes = buffer.tobytes()
                self._encode_count += 1
                alpha = 0.1
                if self._encode_count == 1:
                    self._avg_stream_ms = stream_time_ms
                    self._avg_total_latency_ms = total_latency_ms
                else:
                    self._avg_stream_ms = (
                        alpha * stream_time_ms + (1 - alpha) * self._avg_stream_ms
                    )
                    self._avg_total_latency_ms = (
                        alpha * total_latency_ms + (1 - alpha) * self._avg_total_latency_ms
                    )

                try:
                    self._queues.stream_queue.put_nowait(jpeg_bytes)
                except queue.Full:
                    # Drop oldest frame and push the fresh one
                    self._drop_count += 1
                    try:
                        self._queues.stream_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queues.stream_queue.put_nowait(jpeg_bytes)

                if self._encode_count % 30 == 0:
                    logger.info(
                        "perf stream frame=%d capture_time_ms=%.1f inference_time_ms=%.1f tracking_time_ms=%.1f behavior_time_ms=%.1f stream_time_ms=%.1f total_latency_ms=%.1f stream_queue=%d",
                        packet.frame_index,
                        packet.capture_time_ms,
                        packet.inference_time_ms,
                        packet.tracking_time_ms,
                        packet.behavior_time_ms,
                        stream_time_ms,
                        total_latency_ms,
                        self._queues.stream_queue.qsize(),
                    )

            except Exception:
                logger.exception("Error in encode loop")
                time.sleep(0.1)

        logger.info("Encode loop exited")

    @property
    def is_running(self) -> bool:
        """Return whether the stream worker is active."""
        return self._is_running

    @property
    def encode_count(self) -> int:
        """Return the total number of frames encoded."""
        return self._encode_count

    @property
    def stats(self) -> dict:
        """Return stream worker statistics."""
        return {
            "is_running": self._is_running,
            "frames_encoded": self._encode_count,
            "avg_stream_ms": round(self._avg_stream_ms, 1),
            "avg_total_latency_ms": round(self._avg_total_latency_ms, 1),
            "frames_dropped": self._drop_count,
        }
