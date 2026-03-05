"""
OVERWATCH — Video Capture Service
====================================
Handles video source connection, frame capture, and frame
preprocessing using OpenCV.

Supports webcam, video file, and RTSP stream inputs.
"""

import cv2
import numpy as np
import logging
from typing import Optional

from app.config import Settings

logger = logging.getLogger(__name__)


class VideoService:
    """
    Manages video source capture using OpenCV.

    Handles opening, reading, and releasing video sources.
    Performs frame resizing to meet resolution constraints.

    Attributes:
        _settings: Application configuration.
        _capture: OpenCV VideoCapture instance.
        _is_running: Whether the capture is actively reading frames.
        _source: The video source identifier.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the VideoService.

        Args:
            settings: Application configuration with video parameters.
        """
        self._settings: Settings = settings
        self._capture: Optional[cv2.VideoCapture] = None
        self._is_running: bool = False
        self._source: str = settings.video_source

    def start(self, source: Optional[str] = None) -> bool:
        """
        Open the video source and begin capturing.

        Args:
            source: Optional override for video source.
                    Can be "0" for webcam, a file path, or RTSP URL.

        Returns:
            bool: True if the source was opened successfully.
        """
        if source is not None:
            self._source = source

        # Try integer conversion for webcam index
        capture_source: int | str
        try:
            capture_source = int(self._source)
        except ValueError:
            capture_source = self._source

        self._capture = cv2.VideoCapture(capture_source)

        if not self._capture.isOpened():
            logger.error("Failed to open video source: %s", self._source)
            self._is_running = False
            return False

        # Set capture properties
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._settings.frame_width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._settings.frame_height)

        self._is_running = True
        logger.info(
            "Video source opened: %s (%dx%d)",
            self._source,
            int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        return True

    def read_frame(self) -> Optional[np.ndarray]:
        """
        Read a single frame from the video source.

        Automatically resizes the frame if it exceeds the
        configured maximum resolution.

        Returns:
            np.ndarray or None: The captured frame (BGR), or None if
                                the read failed or source is not open.
        """
        if self._capture is None or not self._is_running:
            return None

        ret, frame = self._capture.read()

        if not ret:
            logger.warning("Failed to read frame from source: %s", self._source)
            return None

        # Enforce maximum resolution
        frame = self._resize_frame(frame)
        return frame

    def _resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Resize a frame to fit within the maximum resolution constraint.

        Maintains aspect ratio. Only downsizes, never upsizes.

        Args:
            frame: Input BGR frame.

        Returns:
            np.ndarray: Resized frame if necessary, otherwise original.
        """
        max_dim = self._settings.pipeline_max_resolution
        h, w = frame.shape[:2]

        if max(h, w) <= max_dim:
            return frame

        scale = max_dim / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    def stop(self) -> None:
        """Release the video source and stop capturing."""
        self._is_running = False
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            logger.info("Video source released: %s", self._source)

    @property
    def is_running(self) -> bool:
        """Return whether the video service is actively capturing."""
        return self._is_running

    @property
    def source_info(self) -> dict:
        """
        Return metadata about the current video source.

        Returns:
            dict: Source information including dimensions and FPS.
        """
        if self._capture is None or not self._capture.isOpened():
            return {"source": self._source, "status": "closed"}

        return {
            "source": self._source,
            "status": "open",
            "width": int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": int(self._capture.get(cv2.CAP_PROP_FPS)),
        }
