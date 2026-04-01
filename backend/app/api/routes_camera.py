"""
OVERWATCH — Camera API Routes
================================
Endpoints for camera pipeline control and MJPEG streaming.
"""

import asyncio
import logging
import queue
from typing import AsyncIterator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import Settings
from app.core.event_bus import EventBus
from app.core.queues import PipelineQueues
from app.schemas.camera_schema import CameraStartRequest
from app.services.video_service import VideoService
from app.services.detection_service import DetectionService
from app.services.alert_service import AlertService
from app.services.face.face_service import FaceService
from app.pipelines.video_pipeline import VideoPipeline
from app.api.routes_alerts import init_alert_routes
from app.api.routes_faces import init_face_routes
from app.api.routes_system import init_system_routes
from app.api.routes_zones import init_zone_routes
from app.core.dependencies import get_module_controller, get_system_monitor
from app.services.zone_service import ZoneService

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
    alert_service = AlertService(settings)
    module_controller = get_module_controller()
    # FaceService() is always created so DB endpoints (list/delete) remain
    # functional.  InsightFace models are NOT loaded here — load_model() is
    # only called inside VideoPipeline.start() when face_service is non-None.
    face_service = FaceService()

    init_alert_routes(alert_service)
    init_face_routes(face_service)

    # Zone service — load from DB once, cache in memory
    zone_service = ZoneService()
    zone_service.load_zones()
    init_zone_routes(zone_service)

    # Only inject face_service into the pipeline when the feature flag is on.
    # Passing None prevents model loading and keeps the pipeline free of any
    # face-recognition CPU cost.
    pipeline_face_service = face_service if settings.enable_face_recognition else None

    _pipeline = VideoPipeline(
        settings=settings,
        event_bus=event_bus,
        video_service=video_service,
        detection_service=detection_service,
        queues=queues,
        alert_service=alert_service,
        face_service=pipeline_face_service,
        module_controller=module_controller,
        zone_service=zone_service,
    )

    # Wire up the SystemMonitor with all required references
    system_monitor = get_system_monitor()
    system_monitor.set_pipeline(_pipeline)
    system_monitor.set_module_controller(module_controller)
    init_system_routes(module_controller, _pipeline, system_monitor)

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


async def _mjpeg_generator() -> AsyncIterator[bytes]:
    """
    Async generator that yields MJPEG multipart frames from stream_queue.

    Reads JPEG bytes from the stream queue and wraps them in
    the multipart/x-mixed-replace boundary format.

    Uses run_in_executor to offload the blocking queue.get() call
    so the asyncio event loop is never blocked.

    Yields:
        bytes: MJPEG multipart frame chunk.
    """
    pipeline: VideoPipeline = _pipeline  # type: ignore[assignment]
    queues: PipelineQueues = _queues  # type: ignore[assignment]

    if queues is None or pipeline is None:
        return

    loop = asyncio.get_running_loop()

    while pipeline.is_running:
        try:
            # Offload blocking queue.get() to a thread pool so we
            # never stall the asyncio event loop while waiting.
            jpeg_bytes: bytes = await loop.run_in_executor(
                None, lambda: queues.stream_queue.get(timeout=0.5)  # type: ignore[arg-type]
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
    If the pipeline is already running, returns a success response immediately
    so the start flow is idempotent (safe to call multiple times).
    """
    pipeline = _get_pipeline()
    requested_source = request.source or pipeline.stats.get("source", {}).get("source")

    logger.info("Camera start requested (source=%s)", requested_source)

    if pipeline.is_running:
        logger.info("Camera start request received but pipeline is already running — returning success")
        return {"message": "Pipeline already running", "stats": pipeline.stats}

    success = await pipeline.start(source=request.source)

    if not success:
        logger.error("Camera start failed (source=%s)", requested_source)
        raise HTTPException(
            status_code=500,
            detail="Failed to start pipeline. Check video source and model.",
        )

    logger.info("Camera pipeline start request completed successfully")
    return {"message": "Pipeline started", "stats": pipeline.stats}


@router.post("/stop")
async def stop_pipeline() -> dict:
    """
    Stop the video processing pipeline.

    Releases video source and stops processing.
    """
    pipeline = _get_pipeline()

    logger.info("Camera stop requested")

    if not pipeline.is_running:
        logger.warning("Camera stop request ignored because pipeline is not running")
        raise HTTPException(
            status_code=409,
            detail="Pipeline is not running",
        )

    await pipeline.stop()
    logger.info("Camera pipeline stop request completed successfully")
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
