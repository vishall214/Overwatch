"""
OVERWATCH — Alert API Routes
================================
Endpoints for alert management and retrieval.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.alert_schema import AlertListResponse, AlertResponse
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])

# ── Service singleton (initialized during startup) ──────────────
_alert_service: Optional[AlertService] = None


def init_alert_routes(alert_service: AlertService) -> None:
    """Inject the AlertService singleton into this module."""
    global _alert_service
    _alert_service = alert_service


def _get_alert_service() -> AlertService:
    if _alert_service is None:
        raise HTTPException(
            status_code=503,
            detail="Alert service not initialized",
        )
    return _alert_service


@router.get("", response_model=AlertListResponse)
async def list_alerts(limit: int = 100) -> AlertListResponse:
    """
    List recent alerts, newest first.

    Args:
        limit: Maximum number of alerts to return.

    Returns:
        AlertListResponse: List of recent alerts.
    """
    service = _get_alert_service()
    rows = service.get_alerts(limit=limit)
    alerts = [
        AlertResponse(
            id=r.id,
            event_type=r.event_type,
            timestamp=r.timestamp,
            track_id=r.track_id,
            zone=r.zone or "",
            metadata=r.metadata_ or {},
            snapshot_path=r.snapshot_path or "",
        )
        for r in rows
    ]
    return AlertListResponse(
        alerts=alerts,
        total=service.get_alert_count(),
    )


@router.patch("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int) -> dict:
    """Acknowledge an alert (Phase 3 stub)."""
    return {"message": f"Alert {alert_id} acknowledge stub (Phase 3)"}


@router.patch("/{alert_id}/resolve")
async def resolve_alert(alert_id: int) -> dict:
    """Resolve an alert (Phase 3 stub)."""
    return {"message": f"Alert {alert_id} resolve stub (Phase 3)"}
