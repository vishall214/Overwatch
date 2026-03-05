"""
OVERWATCH — Thread-Safe Pipeline Queues
==========================================
Defines the shared queues used by pipeline workers to pass
frames and results between processing stages.

Architecture:
    CaptureWorker → frame_queue → InferenceWorker → detection_queue
                                                   → StreamWorker → stream_queue → MJPEG endpoint

All queues use Python's thread-safe queue.Queue with fixed
maximum sizes to prevent memory buildup and backpressure.
"""

import logging
import queue
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FramePacket:
    """
    Data packet passed through the frame queue.

    Attributes:
        frame: Raw BGR frame as numpy array.
        frame_index: Sequential frame counter.
        timestamp_ns: Capture timestamp in nanoseconds (monotonic clock).
    """

    frame: np.ndarray
    frame_index: int
    timestamp_ns: int


@dataclass
class DetectionPacket:
    """
    Data packet passed through the detection queue.

    Attributes:
        frame: Original BGR frame.
        annotated_frame: Frame with bounding boxes drawn.
        detections: List of detection dictionaries.
        frame_index: Sequential frame counter.
        timestamp_ns: Original capture timestamp in nanoseconds.
    """

    frame: np.ndarray
    annotated_frame: np.ndarray
    detections: list[dict[str, Any]]
    frame_index: int
    timestamp_ns: int


class PipelineQueues:
    """
    Container for all thread-safe queues used in the video pipeline.

    Manages creation, access, and cleanup of inter-worker queues.
    Sizes are intentionally small to keep latency low and prevent
    memory buildup.

    Attributes:
        frame_queue: Raw frames from capture worker → inference worker.
        detection_queue: Detection results → stream worker.
        stream_queue: Encoded JPEG bytes → MJPEG endpoint.
    """

    def __init__(self) -> None:
        """
        Initialize pipeline queues with fixed sizes.

        Sizes are tuned for low-latency CPU pipelines:
          - frame_queue(5):     absorbs capture/inference speed mismatch
          - detection_queue(5): absorbs inference/encode speed mismatch
          - stream_queue(2):    keeps only the freshest frames for streaming
        """
        self.frame_queue: queue.Queue[FramePacket] = queue.Queue(maxsize=5)
        self.detection_queue: queue.Queue[DetectionPacket] = queue.Queue(maxsize=5)
        self.stream_queue: queue.Queue[bytes] = queue.Queue(maxsize=2)

        logger.info(
            "Pipeline queues initialized (frame=5, detection=5, stream=2)",
        )

    def clear_all(self) -> None:
        """
        Drain all queues, discarding any pending items.

        Called during pipeline shutdown to free memory.
        """
        for q, name in [
            (self.frame_queue, "frame_queue"),
            (self.detection_queue, "detection_queue"),
            (self.stream_queue, "stream_queue"),
        ]:
            count = 0
            while not q.empty():
                try:
                    q.get_nowait()
                    count += 1
                except queue.Empty:
                    break
            if count > 0:
                logger.debug("Cleared %d items from %s", count, name)

    @property
    def stats(self) -> dict[str, int]:
        """
        Return current queue fill levels.

        Returns:
            dict: Queue name → current item count.
        """
        return {
            "frame_queue": self.frame_queue.qsize(),
            "detection_queue": self.detection_queue.qsize(),
            "stream_queue": self.stream_queue.qsize(),
        }
