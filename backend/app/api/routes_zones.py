"""
OVERWATCH — Zone API Routes
================================
Endpoints for zone management (CRUD).
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.database.crud import create_zone, get_zones, delete_zone
from app.database.database import SessionLocal
from app.schemas.zone_schema import ZoneCreate, ZoneListResponse, ZoneResponse
from app.services.zone_service import ZoneService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zones", tags=["Zones"])

# ── Service singleton (initialized during startup) ──────────────
_zone_service: Optional[ZoneService] = None


def init_zone_routes(zone_service: ZoneService) -> None:
    """Inject the ZoneService singleton into this module."""
    global _zone_service
    _zone_service = zone_service


def _get_zone_service() -> ZoneService:
    if _zone_service is None:
        raise HTTPException(
            status_code=503,
            detail="Zone service not initialized",
        )
    return _zone_service


@router.get("", response_model=ZoneListResponse)
async def list_zones() -> ZoneListResponse:
    """List all active zones (from cache)."""
    service = _get_zone_service()
    cached = service.get_zones()
    zones = [ZoneResponse(**z, is_active=True, created_at="2000-01-01T00:00:00") for z in cached]
    # Re-fetch from DB for accurate created_at
    db = SessionLocal()
    try:
        rows = get_zones(db)
        zones = [
            ZoneResponse(
                id=r.id,
                name=r.name,
                type=r.type,
                x=r.x,
                y=r.y,
                width=r.width,
                height=r.height,
                camera_id=r.camera_id or "default",
                is_active=r.is_active if r.is_active is not None else True,
                created_at=r.created_at,
            )
            for r in rows
        ]
    finally:
        db.close()
    return ZoneListResponse(zones=zones, total=len(zones))


@router.post("", response_model=ZoneResponse, status_code=201)
async def add_zone(payload: ZoneCreate) -> ZoneResponse:
    """Create a new zone and reload cache."""
    service = _get_zone_service()
    db = SessionLocal()
    try:
        row = create_zone(
            db,
            zone_type=payload.type,
            x=payload.x,
            y=payload.y,
            width=payload.width,
            height=payload.height,
            name=payload.name,
            camera_id=payload.camera_id,
        )
        service.reload()
        return ZoneResponse(
            id=row.id,
            name=row.name,
            type=row.type,
            x=row.x,
            y=row.y,
            width=row.width,
            height=row.height,
            camera_id=row.camera_id or "default",
            is_active=row.is_active if row.is_active is not None else True,
            created_at=row.created_at,
        )
    finally:
        db.close()


@router.delete("/{zone_id}")
async def remove_zone(zone_id: int) -> dict:
    """Delete a zone and reload cache."""
    service = _get_zone_service()
    db = SessionLocal()
    try:
        deleted = delete_zone(db, zone_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Zone not found")
        service.reload()
        return {"message": f"Zone {zone_id} deleted"}
    finally:
        db.close()
