"""
OVERWATCH — Face Recognition API Routes
==========================================
Endpoints for watchlist face enrolment and listing.
"""

import logging
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.database.database import SessionLocal
from app.database.crud import create_face_row, get_all_faces, delete_face_by_name
from app.core.security import get_current_user
from app.services.face.face_service import FaceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/faces", tags=["Face DB"])

# ── Service singleton (set during startup) ──────────────────────
_face_service: Optional[FaceService] = None


def init_face_routes(face_service: FaceService) -> None:
    """Inject the FaceService singleton into this module."""
    global _face_service
    _face_service = face_service


def _get_face_service() -> FaceService:
    if _face_service is None:
        raise HTTPException(
            status_code=503,
            detail="Face service not initialized",
        )
    return _face_service


@router.post("/register")
async def register_face(
    name: str = Form(...),
    image: UploadFile = File(...),
    _: int = Depends(get_current_user),
) -> dict:
    """
    Register a new watchlist face.

    Accepts a name and an image file, detects the face,
    generates a 512-d embedding, and stores it in PostgreSQL.
    """
    service = _get_face_service()

    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    embedding = service.get_embedding(frame)
    if embedding is None:
        raise HTTPException(
            status_code=400,
            detail="No face detected in the image",
        )

    db = SessionLocal()
    try:
        row = create_face_row(db, name=name, embedding=embedding.tolist())
    finally:
        db.close()

    # Reload the FAISS index so the new face is immediately searchable
    service.index.reload()

    logger.info("Face registered: %s (id=%d)", name, row.id)
    return {"message": f"Face '{name}' registered", "face_id": row.id}


@router.get("")
async def list_faces() -> dict:
    """List all enrolled watchlist faces."""
    db = SessionLocal()
    try:
        faces = get_all_faces(db)
    finally:
        db.close()

    return {
        "identities": [
            {
                "id": f.id,
                "name": f.name,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in faces
        ],
        "total": len(faces),
    }


@router.delete("/{name}")
async def remove_face(name: str, _: int = Depends(get_current_user)) -> dict:
    """Remove an enrolled face identity by name."""
    service = _get_face_service()

    db = SessionLocal()
    try:
        deleted = delete_face_by_name(db, name)
    finally:
        db.close()

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Face '{name}' not found")

    service.index.reload()
    logger.info("Face removed: %s", name)
    return {"message": f"Face '{name}' removed"}
