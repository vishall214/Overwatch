"""
OVERWATCH — Monitoring API Routes
=====================================
Snapshot serving endpoint.  Pipeline metrics and alert stats
are registered on the existing /system router in routes_system.py
so there are no path conflicts.

Routes:
    GET /snapshots/{filename}  — serve a stored alert snapshot image
"""

import logging
import os
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Monitoring"])

# Whitelist: only alphanumeric, underscores, hyphens, dots allowed
_SAFE_FILENAME = re.compile(r"^[\w\-]+\.(jpg|jpeg|png)$", re.IGNORECASE)


@router.get("/snapshots/{filename}")
async def get_snapshot(filename: str) -> FileResponse:
    """
    Serve a stored alert snapshot image.

    The frontend uses this to display alert thumbnails.
    Only files inside the configured snapshots directory are served.

    Args:
        filename: Image filename (e.g. intrusion_20260311_095911.jpg).

    Returns:
        FileResponse: The image file.
    """
    if not _SAFE_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    settings = get_settings()
    filepath = os.path.join(settings.snapshots_dir, filename)

    # Resolve to prevent directory traversal
    real_base = os.path.realpath(settings.snapshots_dir)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(real_base):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.isfile(real_path):
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return FileResponse(real_path, media_type="image/jpeg")
