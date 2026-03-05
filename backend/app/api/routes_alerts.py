"""
OVERWATCH — Alert API Routes
================================
Stub endpoints for alert management.

Phase 1: Returns empty responses.
Full implementation in Phase 3.
"""

import logging
from typing import Optional

from fastapi import APIRouter

from app.schemas.alert_schema import AlertListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
) -> AlertListResponse:
    """
    List all alerts with optional filters.
    Returns:
        AlertListResponse: List of matching alerts.
    """
    return AlertListResponse(alerts=[], total=0)


@router.patch("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int) -> dict:
    """
    Acknowledge an alert.
    Args:
        alert_id: ID of the alert to acknowledge.
    """
    return {"message": f"Alert {alert_id} acknowledge stub (Phase 3)"}


@router.patch("/{alert_id}/resolve")
async def resolve_alert(alert_id: int) -> dict:
    """
    Resolve an alert.
    Args:
        alert_id: ID of the alert to resolve.
    """
    return {"message": f"Alert {alert_id} resolve stub (Phase 3)"}
