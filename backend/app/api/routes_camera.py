"""
OVERWATCH — Camera API Routes
================================
Endpoints for camera pipeline control and MJPEG streaming.
"""

import asyncio
import logging
import queue
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import Settings
from app.core.event_bus import EventBus
from app.core.queues import PipelineQueues
from app.schemas.camera_schema import (
    CameraStartRequest,
    CameraStatusResponse,
)
from app.services.video_service import VideoService
from app.services.detection_service import DetectionService
from app.pipelines.video_pipeline import VideoPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/camera", tags=["Camera"])

# ── Service singletons (initialized in main.py lifespan) ────────
_pipeline: Optional[VideoPipeline] = None
_queues: Optional[PipelineQueues] = None


def init_camera_services(
    settings: Settings,
    event_bus: EventBus,
    queues: PipelineQueues,
) -> VideoPipeline:
    """
    Initialize camera-related services and pipeline.

    Called once during application startup to create service
    singletons and wire them together.

    Args:
        settings: Application configuration.
        event_bus: Internal event bus.
        queues: Thread-safe inter-worker queues.

    Returns:
        VideoPipeline: The initialized video pipeline.
    """
    global _pipeline, _queues

    _queues = queues

    video_service = VideoService(settings)
    detection_service = DetectionService(settings)

    _pipeline = VideoPipeline(
        settings=settings,
        event_bus=event_bus,
        video_service=video_service,
        detection_service=detection_service,
        queues=queues,
    )

    logger.info("Camera services initialized")
    return _pipeline


def _get_pipeline() -> VideoPipeline:
    """
    Get the video pipeline instance.

    Returns:
        VideoPipeline: The active pipeline.

    Raises:
        HTTPException: If services are not initialized.
    """
    if _pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Camera services not initialized",
        )
    return _pipeline


async def _mjpeg_generator() -> AsyncGenerator[bytes, None]:
    """
    Async generator that yields MJPEG multipart frames from stream_queue.

    Reads JPEG bytes from the stream queue and wraps them in
    the multipart/x-mixed-replace boundary format.

    Uses run_in_executor to offload the blocking queue.get() call
    so the asyncio event loop is never blocked.

    Yields:
        bytes: MJPEG multipart frame chunk.
    """
    if _queues is None or _pipeline is None:
        return

    loop = asyncio.get_running_loop()

    while _pipeline.is_running:
        try:
            # Offload blocking queue.get() to a thread pool so we
            # never stall the asyncio event loop while waiting.
            jpeg_bytes: bytes = await loop.run_in_executor(
                None,
                lambda: _queues.stream_queue.get(timeout=0.5),
            )
        except queue.Empty:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + jpeg_bytes
            + b"\r\n"
        )

        # Brief yield to keep the event loop responsive
        await asyncio.sleep(0.001)


@router.post("/start")
async def start_pipeline(
    request: CameraStartRequest = CameraStartRequest(),
) -> dict:
    """
    Start the video processing pipeline.

    Accepts an optional video source override.
    Returns pipeline status after starting.
    """
    pipeline = _get_pipeline()

    if pipeline.is_running:
        raise HTTPException(
            status_code=409,
            detail="Pipeline is already running",
        )

    success = await pipeline.start(source=request.source)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to start pipeline. Check video source and model.",
        )

    return {"message": "Pipeline started", "stats": pipeline.stats}


@router.post("/stop")
async def stop_pipeline() -> dict:
    """
    Stop the video processing pipeline.

    Releases video source and stops processing.
    """
    pipeline = _get_pipeline()

    if not pipeline.is_running:
        raise HTTPException(
            status_code=409,
            detail="Pipeline is not running",
        )

    await pipeline.stop()
    return {"message": "Pipeline stopped"}


@router.get("/status")
async def pipeline_status() -> dict:
    """
    Get the current status of the video pipeline.

    Returns pipeline statistics including worker states and queue levels.
    """
    pipeline = _get_pipeline()
    return pipeline.stats


@router.get("/stream")
async def mjpeg_stream() -> StreamingResponse:
    """
    Stream the processed video feed as MJPEG.

    Returns a multipart/x-mixed-replace streaming response
    that can be consumed directly by an <img> tag in the browser.
    """
    pipeline = _get_pipeline()

    if not pipeline.is_running:
        raise HTTPException(
            status_code=409,
            detail="Pipeline is not running. Start it first via POST /camera/start",
        )

    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
