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
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

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
    # COCO class IDs to detect (0=person)
    detection_classes: list[int] = [0, 56, 67]

    # ── Debug ────────────────────────────────────────────────────
    debug_detection_logs: bool = False

    # ── Streaming ────────────────────────────────────────────────
    stream_quality: int = 80  # JPEG encode quality (1-100)
    stream_fps: int = 15  # Target streaming FPS

    # ── Storage Paths ────────────────────────────────────────────
    weights_dir: str = "weights"
    storage_dir: str = "storage"
    snapshots_dir: str = "storage/snapshots"
    clips_dir: str = "storage/clips"

    # ── Pipeline ─────────────────────────────────────────────────
    pipeline_skip_frames: int = 1  # Capture-stage frame skipping (1 = no skipping)
    inference_skip_frames: int = 1  # Inference-stage skip (1 = no extra skipping)
    pipeline_max_resolution: int = 640
    queue_size: int = 32  # Max items per inter-worker queue

    # ── Face Recognition ────────────────────────────────────────
    enable_face_recognition: bool = False  # Set True to re-enable at runtime
    face_detection_size: int = 320

    # ── Behavior / Intrusion Zones ─────────────────────────────────
    zone_a: list[list[int]] = [[200, 100], [400, 100], [400, 300], [200, 300]]
    loiter_threshold: float = 10.0  # Seconds inside zone before loitering alert
    crowd_threshold: int = 5  # Number of persons in zone before crowd alert

    # ── Weapon / Dangerous Object Detection ──────────────────────
    enable_weapon_detection: bool = True
    weapon_model: str = "yolov8n.pt"  # Uses same pretrained COCO model
    weapon_confidence: float = 0.2
    weapon_skip_frames: int = 3  # Run weapon inference every N frames
    weapon_consecutive_threshold: int = 2  # Consecutive detections before alert
    weapon_cooldown_seconds: float = 10.0  # Seconds between alerts for same object
    weapon_classes: list[int] = [43, 76]  # COCO classes: 43=knife

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





