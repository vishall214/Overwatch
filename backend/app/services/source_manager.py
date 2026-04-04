"""
OVERWATCH — Source Manager
=============================
Unified interface for managing different video sources with direct
cv2.VideoCapture handling:
- Camera (live webcam)
- Demo videos (preloaded)
- User-uploaded videos

Handles source initialization, frame reading, and automatic frame
looping for video files.

Architecture:
    CaptureWorker → SourceManager → [Camera | Demo | Upload]
"""

import cv2
import logging
import os
from typing import Optional
from urllib.parse import urlparse

import numpy as np

logger = logging.getLogger(__name__)

# Base directories (absolute, independent of process working directory)
BACKEND_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORKSPACE_ROOT_DIR = os.path.abspath(os.path.join(BACKEND_ROOT_DIR, ".."))
DEMO_VIDEOS_DIR = os.path.join(BACKEND_ROOT_DIR, "assets", "videos")
UPLOADS_DIR = os.path.join(BACKEND_ROOT_DIR, "uploads")


class SourceManager:
    """
    Manages active video source with unified interface and direct
    cv2.VideoCapture operations.

    Supports camera (live), demo videos, and user-uploaded videos.
    Automatically loops video files when they reach the end.
    Safely handles source switching and resource cleanup.

    Attributes:
        source_type: One of "camera", "demo", "upload", or None.
        source_path: Resolved filesystem path (None for camera).
        source_name: Human-readable name for the active source.
        current_source: The active OpenCV VideoCapture instance.
    """

    def __init__(self) -> None:
        self.source_type: Optional[str] = None
        self.source_path: Optional[str] = None
        self.source_name: str = "None"
        self.current_source: Optional[cv2.VideoCapture] = None

    @staticmethod
    def _is_stream_uri(path: str) -> bool:
        """Return True when the input looks like a network stream URI."""
        scheme = urlparse(path).scheme.lower()
        return scheme in {"rtsp", "http", "https", "rtmp"}

    @staticmethod
    def _resolve_existing_local_path(path: str) -> Optional[str]:
        """
        Resolve an existing local file path.

        Tries both the provided path and a backend-root-relative fallback.
        """
        candidate = os.path.normpath(path)
        if os.path.isfile(candidate):
            return candidate

        if not os.path.isabs(candidate):
            rooted = os.path.normpath(os.path.join(BACKEND_ROOT_DIR, candidate))
            if os.path.isfile(rooted):
                return rooted

            workspace_rooted = os.path.normpath(
                os.path.join(WORKSPACE_ROOT_DIR, candidate)
            )
            if os.path.isfile(workspace_rooted):
                return workspace_rooted

        return None

    def set_source(self, source_type: str, path: Optional[str] = None) -> bool:
        """
        Switch to a new video source with direct cv2.VideoCapture management.

        Safely releases the previous source before initializing the new one.
        Validates source_type and ensures path is provided for demo/upload.

        Args:
            source_type: One of "camera", "demo", or "upload".
            path: File path for demo/upload sources, None for camera.

        Returns:
            bool: True if source was opened successfully.

        Raises:
            ValueError: If source_type is invalid or required path is missing.
            FileNotFoundError: If video file path does not exist.
        """
        # Release previous source
        self.release()

        # Validate source type
        if source_type not in ["camera", "demo", "upload"]:
            raise ValueError(f"Invalid source type: {source_type}")

        # Validate path requirement
        if source_type in ["demo", "upload"] and path is None:
            raise ValueError(f"{source_type} source requires a path")

        resolved_path = path
        if source_type in ["demo", "upload"]:
            assert path is not None
            if self._is_stream_uri(path):
                resolved_path = path
            else:
                local_path = self._resolve_existing_local_path(path)
                if local_path is None:
                    raise FileNotFoundError(f"Unsupported source path: {path}")
                resolved_path = local_path

        self.source_type = source_type
        self.source_path = resolved_path

        try:
            if source_type == "camera":
                camera_index = 0
                if path is not None and str(path).strip() != "":
                    try:
                        camera_index = int(str(path).strip())
                    except ValueError:
                        logger.warning("Invalid camera index '%s', falling back to index 0", path)

                self.current_source = cv2.VideoCapture(camera_index)
                if not self.current_source.isOpened():
                    logger.error("Failed to open camera (index %d)", camera_index)
                    self.current_source = None
                    return False
                self.source_name = f"Live Camera ({camera_index})"
                logger.info("Camera source initialized (index=%d)", camera_index)

            elif source_type in ["demo", "upload"]:
                self.current_source = cv2.VideoCapture(resolved_path)
                if not self.current_source.isOpened():
                    logger.error("Failed to open %s video: %s", source_type, resolved_path)
                    self.current_source = None
                    return False
                label = "Demo" if source_type == "demo" else "Upload"
                source_display = (
                    resolved_path if self._is_stream_uri(str(resolved_path))
                    else os.path.basename(str(resolved_path))
                )
                self.source_name = f"{label}: {source_display}"
                logger.info(
                    "%s source initialized: %s", label, resolved_path
                )

            return True

        except Exception as e:
            logger.error("Error setting source: %s", e)
            self.current_source = None
            return False

    def resolve_source(
        self,
        source_type: str,
        name: Optional[str] = None,
        category: Optional[str] = None,
        path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Resolve source path (legacy method for compatibility).

        Resolves and validates paths without opening captures.

        Args:
            source_type: "camera", "demo", or "upload".
            name: Filename for demo videos (e.g. "crowd_high.mp4").
            category: Demo category subfolder (e.g. "intrusion").
            path: Direct path for uploaded videos.

        Returns:
            Resolved path string, or None for camera.
        """
        if source_type == "camera":
            return None

        if source_type == "demo":
            if not name:
                raise ValueError("Demo source requires a video name")
            cat = category or "general"
            resolved = os.path.join(DEMO_VIDEOS_DIR, cat, name)
            if not os.path.isfile(resolved):
                raise FileNotFoundError(f"Demo video not found: {resolved}")
            return resolved

        if source_type == "upload":
            if not path:
                raise ValueError("Upload source requires a path")
            if self._is_stream_uri(path):
                return path
            resolved = self._resolve_existing_local_path(path)
            if resolved is None:
                raise FileNotFoundError(f"Uploaded video not found: {path}")
            return resolved

        raise ValueError(f"Unknown source type: {source_type}")

    def read(self) -> tuple[bool, Optional[np.ndarray]]:
        """
        Read the next frame from the current source.

        For video files, automatically loops back to the beginning
        when the end is reached.

        Returns:
            tuple: (success: bool, frame: np.ndarray | None)
                   - (False, None) if source not available
                   - (True, frame) if frame read successfully
                   - (False, None) if EOF reached on camera
        """
        if self.current_source is None:
            return False, None

        ret, frame = self.current_source.read()

        # Auto-loop for video files
        if not ret and self.source_type in ["demo", "upload"]:
            try:
                # Reset to beginning
                self.current_source.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.current_source.read()
                if ret:
                    logger.debug("Video auto-looped: %s", self.source_path)
            except Exception as e:
                logger.error("Error auto-looping video: %s", e)

        return ret, frame

    def release(self) -> None:
        """
        Release the current video source and reset state.

        Safely closes the OpenCV VideoCapture and clears references.
        """
        if self.current_source is not None:
            try:
                self.current_source.release()
                logger.info("Source released: %s", self.source_type)
            except Exception as e:
                logger.error("Error releasing source: %s", e)
            finally:
                self.current_source = None

    def clear(self) -> None:
        """
        Reset source state completely.

        Releases any open capture and clears metadata.
        """
        self.release()
        self.source_type = None
        self.source_path = None
        self.source_name = "None"

    @property
    def info(self) -> dict:
        """Return metadata about the current source."""
        return {
            "source_type": self.source_type or "none",
            "source_path": self.source_path or "",
            "source_name": self.source_name,
            "is_open": self.current_source is not None
            and self.current_source.isOpened()
            if self.current_source is not None
            else False,
        }

    @staticmethod
    def list_demo_videos(category: str) -> list[str]:
        """
        List available demo video files for a category.

        Args:
            category: Subfolder name (e.g. "intrusion", "loitering", "crowd").

        Returns:
            Sorted list of video filenames.
        """
        folder = os.path.join(DEMO_VIDEOS_DIR, category)
        if not os.path.isdir(folder):
            return []
        valid_ext = {".mp4", ".avi", ".mkv", ".mov"}
        return sorted(
            f for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in valid_ext
        )
