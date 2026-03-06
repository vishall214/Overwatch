"""
OVERWATCH — Application Configuration
=======================================
All configurable thresholds and settings for the system.
Loaded from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Central configuration for the OVERWATCH system.

    All thresholds and parameters are configurable via environment
    variables or a .env file.
    """

    # ── Application ──────────────────────────────────────────────
    app_name: str = "OVERWATCH"
    app_version: str = "0.1.0"
    debug: bool = True

    # ── Server ───────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000"]

    # ── Video Capture ────────────────────────────────────────────
    video_source: str = "0"  # "0" for webcam, or file path / RTSP URL
    frame_width: int = 640
    frame_height: int = 480
    capture_fps: int = 30

    # ── Detection (YOLOv8) ───────────────────────────────────────
    detection_model: str = "yolov8n.pt"
    detection_confidence: float = 0.5
    detection_iou_threshold: float = 0.45
    detection_max_det: int = 100
    detection_img_size: int = 640
    detection_device: str = "cpu"

    # ── Detection Classes ────────────────────────────────────────
    # COCO class IDs to detect (0=person, 2=car, 56=chair, 39=bottle, 63=laptop, 67=cell phone)
    detection_classes: list[int] = [0, 2, 39, 56, 63, 67]

    # ── Streaming ────────────────────────────────────────────────
    stream_quality: int = 80  # JPEG encode quality (1-100)
    stream_fps: int = 15  # Target streaming FPS

    # ── Storage Paths ────────────────────────────────────────────
    weights_dir: str = "weights"
    storage_dir: str = "storage"
    snapshots_dir: str = "storage/snapshots"
    clips_dir: str = "storage/clips"

    # ── Pipeline ─────────────────────────────────────────────────
    pipeline_skip_frames: int = 0  # 0 = process every frame
    pipeline_max_resolution: int = 640
    queue_size: int = 32  # Max items per inter-worker queue

    model_config = {
        "env_prefix": "OVERWATCH_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_settings() -> Settings:
    """
    Factory function returning a Settings instance.

    Returns:
        Settings: Application configuration loaded from environment.
    """
    return Settings()
