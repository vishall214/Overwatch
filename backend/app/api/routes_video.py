"""
OVERWATCH — Video Source API Routes
======================================
Endpoints for switching video sources, listing demo videos,
and uploading video files.
"""

import logging
import os
import shutil
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query

from app.schemas.video_schema import (
    SourceSwitchRequest,
    SourceSwitchResponse,
    DemoListResponse,
    UploadResponse,
)
from app.core.security import get_current_user
from app.services.source_manager import SourceManager, UPLOADS_DIR
from app.pipelines.video_pipeline import VideoPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["Video Source"])

# ── Service singletons (injected during startup) ────────────────
_pipeline: Optional[VideoPipeline] = None
_source_manager: Optional[SourceManager] = None

# Maximum upload size: 200 MB
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
ALLOWED_EXTENSIONS = {".mp4", ".avi"}


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


@router.post("/source", response_model=SourceSwitchResponse)
async def switch_source(
    request: SourceSwitchRequest,
    _user_id: int = Depends(get_current_user),
) -> SourceSwitchResponse:
    """
    Switch the active video source.

    Changes the source for the active pipeline without stopping it.
    Automatically resets behavior worker event state to prevent
    stale detections from previous source.

    Accepts: camera, demo, or upload source types.
    """
    pipeline, source_mgr = _get_deps()

    logger.info(
        "Source switch requested: type=%s name=%s category=%s path=%s",
        request.type, request.name, request.category, request.path,
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

    # Switch source via pipeline (blocking call → executor)
    try:
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(
            None,
            pipeline.switch_source,
            request.type,
            resolved_path,
        )
        
        if not success:
            raise Exception("Pipeline switch_source returned False")
            
    except Exception as exc:
        logger.exception("Source switch failed")
        raise HTTPException(status_code=500, detail=f"Source switch failed: {exc}")

    return SourceSwitchResponse(
        message=f"Source switched to {source_mgr.source_name}",
        source_type=source_mgr.source_type or "none",
        source_name=source_mgr.source_name,
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
    _user_id: int = Depends(get_current_user),
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
        message=f"Video uploaded: {safe_name}",
        filename=safe_name,
        path=filepath,
    )


@router.get("/source/info")
async def source_info() -> dict:
    """Return metadata about the current active source."""
    _, source_mgr = _get_deps()
    return source_mgr.info
