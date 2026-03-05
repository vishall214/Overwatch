"""
OVERWATCH — Camera API Schemas
=================================
Pydantic schemas for camera-related API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class CameraStartRequest(BaseModel):
    """
    Schema for starting a camera pipeline.

    Attributes:
        source: Video source identifier (webcam index, file path, RTSP URL).
    """

    source: Optional[str] = Field(
        default=None,
        description="Video source: '0' for webcam, file path, or RTSP URL. "
                    "Uses config default if not provided.",
    )


class CameraStatusResponse(BaseModel):
    """
    Schema for camera/pipeline status response.

    Attributes:
        is_running: Whether the pipeline is active.
        frames_processed: Total frames processed.
        current_fps: Current processing frames per second.
        source: Video source information.
        detection: Detection model information.
    """

    is_running: bool
    frames_processed: int
    current_fps: float
    source: dict
    detection: dict


class HealthResponse(BaseModel):
    """
    Schema for health check response.

    Attributes:
        status: Service status string.
        version: Application version string.
    """

    status: str
    version: str
