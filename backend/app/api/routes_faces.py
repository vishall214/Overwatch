"""
OVERWATCH — Face Recognition API Routes
==========================================
Stub endpoints for face enrollment and management.
"""

import logging
from typing import Optional

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/faces", tags=["Face DB"])


@router.get("")
async def list_enrolled_faces() -> dict:
    """
    List all enrolled face identities.

    Phase 1: Stub endpoint.

    Returns:
        dict: List of enrolled identities (empty in Phase 1).
    """
    return {"identities": [], "total": 0}


@router.post("/enroll")
async def enroll_face(name: str) -> dict:
    """
    Enroll a new face identity.

    Phase 1: Stub endpoint.

    Args:
        name: Name/label for the identity to enroll.
    """
    return {"message": f"Enroll face stub for '{name}' (Phase 4)"}


@router.delete("/{name}")
async def remove_face(name: str) -> dict:
    """
    Remove an enrolled face identity.

    Phase 1: Stub endpoint.

    Args:
        name: Name/label of the identity to remove.
    """
    return {"message": f"Remove face stub for '{name}' (Phase 4)"}
