"""
OVERWATCH — Video Source API Routes
======================================
Endpoints for switching video sources, listing demo videos,
and uploading video files.
"""

import logging
import os
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query

from app.schemas.video_schema import (
    SourceSwitchRequest,
    SourceSwitchResponse,
    DemoListResponse,
    UploadResponse,
)
from app.services.source_manager import SourceManager, UPLOADS_DIR
from app.pipelines.video_pipeline import VideoPipeline
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["Video Source"])

# ── Service singletons (injected during startup) ────────────────
_pipeline: Optional[VideoPipeline] = None
_source_manager: Optional[SourceManager] = None

# Maximum upload size: 200 MB
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
ALLOWED_EXTENSIONS = {".mp4", ".avi"}
SUPPORTED_MODULES = {"intrusion", "loitering", "crowd", "weapon_detection"}


def _normalize_module_name(module: Optional[str]) -> Optional[str]:
    if module is None:
        return None
    normalized = module.strip().lower()
    if normalized == "weapons":
        return "weapon_detection"
    if normalized in SUPPORTED_MODULES:
        return normalized
    raise HTTPException(status_code=400, detail=f"Unsupported module '{module}'")


def init_video_routes(
    pipeline: VideoPipeline,
    source_manager: SourceManager,
) -> None:
    """Inject service singletons into this module."""
    global _pipeline, _source_manager
    _pipeline = pipeline
    _source_manager = source_manager


def _get_deps() -> tuple[VideoPipeline, SourceManager]:
    if _pipeline is None or _source_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Video services not initialized",
        )
    return _pipeline, _source_manager


def _resolve_upload_file_path(filename: str) -> str:
    """Resolve a safe absolute path for a filename under UPLOADS_DIR."""
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    uploads_root = os.path.abspath(UPLOADS_DIR)
    file_path = os.path.abspath(os.path.join(uploads_root, safe_name))

    if os.path.commonpath([uploads_root, file_path]) != uploads_root:
        raise HTTPException(status_code=400, detail="Invalid filename path")

    return file_path


@router.post("/source", response_model=SourceSwitchResponse)
async def switch_source(
    request: SourceSwitchRequest,
    _: int = Depends(get_current_user),
) -> SourceSwitchResponse:
    """
    Switch the active video source.

    Changes the source for the active pipeline without stopping it.
    Automatically resets behavior worker event state to prevent
    stale detections from previous source.

    Accepts: camera, demo, or upload source types.
    """
    pipeline, source_mgr = _get_deps()
    normalized_module = _normalize_module_name(request.module)

    logger.info(
        "Source switch requested: type=%s module=%s name=%s category=%s path=%s",
        request.type, normalized_module, request.name, request.category, request.path,
    )

    try:
        resolved_path = source_mgr.resolve_source(
            source_type=request.type,
            name=request.name,
            category=request.category,
            path=request.path,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    target_source_for_start = "0" if request.type == "camera" else resolved_path

    # Switch source via pipeline (or start pipeline if it is currently stopped)
    try:
        if not pipeline.is_running:
            pipeline.set_active_module(normalized_module)
            logger.info(
                "Pipeline is stopped; starting directly with requested source: %s",
                target_source_for_start,
            )
            started = await pipeline.start(source=target_source_for_start)
            if not started:
                raise Exception("Pipeline start failed for requested source")
        else:
            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(
                None,
                pipeline.switch_source,
                request.type,
                resolved_path,
                normalized_module,
            )

            if not success:
                raise Exception(
                    "Unable to activate requested source. "
                    "Verify source availability (camera/file/path) and try again."
                )

    except Exception as exc:
        logger.exception("Source switch failed")
        raise HTTPException(status_code=500, detail=f"Source switch failed: {exc}")

    source_info = pipeline.current_source_info
    source_type = source_info.get("source_type", request.type)
    source_name = source_info.get("source_name", "Unknown")

    return SourceSwitchResponse(
        success=True,
        message=f"Source switched to {source_name}",
        source_type=source_type,
        source_name=source_name,
    )


@router.get("/demo/list", response_model=DemoListResponse)
async def list_demo_videos(
    category: str = Query(
        default="intrusion",
        description="Demo category: intrusion, loitering, or crowd",
    ),
) -> DemoListResponse:
    """List available demo videos for a category."""
    videos = SourceManager.list_demo_videos(category)
    return DemoListResponse(category=category, videos=videos)


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    _: int = Depends(get_current_user),
) -> UploadResponse:
    """
    Upload a video file for analysis.

    Constraints:
    - Only .mp4 and .avi files accepted
    - Maximum size: 200 MB
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate extension
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content) / 1024 / 1024:.1f} MB). Max: {MAX_UPLOAD_BYTES / 1024 / 1024:.0f} MB",
        )

    # Save to uploads directory
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    safe_name = file.filename.replace(" ", "_")
    filepath = os.path.join(UPLOADS_DIR, safe_name)

    with open(filepath, "wb") as f:
        f.write(content)

    logger.info("Video uploaded: %s (%d bytes)", filepath, len(content))

    return UploadResponse(
        success=True,
        message=f"Video uploaded: {safe_name}",
        filename=safe_name,
        path=filepath,
        size_mb=round(len(content) / (1024 * 1024), 2),
    )


@router.delete("/upload/{filename}")
async def delete_upload(
    filename: str,
    _: int = Depends(get_current_user),
) -> dict:
    """Delete an uploaded video by filename."""
    pipeline, _ = _get_deps()
    file_path = _resolve_upload_file_path(filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    # If deleting the currently active source, stop pipeline first and clear source metadata.
    current_info = pipeline.current_source_info
    current_source_path = current_info.get("source_path") or current_info.get("source")
    is_active_source = False
    if current_source_path:
        active_path = os.path.abspath(str(current_source_path))
        is_active_source = os.path.normcase(active_path) == os.path.normcase(file_path)

    if is_active_source:
        if pipeline.is_running:
            try:
                await pipeline.stop()
                logger.info("Pipeline stopped before deleting active upload source")
            except Exception as exc:
                logger.exception("Failed stopping pipeline before source delete")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to stop pipeline before deleting source: {exc}",
                )

        pipeline.reset_source_to_default()
        logger.info("Active upload source cleared; system returned to no-source state")

    try:
        os.remove(file_path)
    except OSError as exc:
        logger.exception("Failed to delete uploaded video: %s", file_path)
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {exc}")

    logger.info("Uploaded video deleted: %s", file_path)
    return {"message": f"Deleted uploaded video: {filename}", "filename": filename}


@router.get("/source/info")
async def source_info() -> dict:
    """Return metadata about the current active source."""
    pipeline, _ = _get_deps()
    return pipeline.current_source_info
