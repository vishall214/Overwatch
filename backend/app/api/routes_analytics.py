"""
OVERWATCH — Analytics API Routes
===================================
Endpoints for retrieving analytics data.

Provides:
- Alert trends over time
- Event distribution
- Summary metrics
- Recent activity

All queries use SQL aggregation for performance.
No heavy backend processing.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.database.database import SessionLocal
from app.core.security import get_current_user
from app.database.models import AlertRow
from app.database.crud import (
    get_alerts_over_time,
    get_event_distribution,
    get_alert_summary,
    get_threat_metrics,
)
from app.utils.snapshot_utils import build_snapshot_url, extract_snapshot_filename

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/alerts-over-time")
async def alerts_over_time(
    interval: str = "minute",
    range_: str = "1h",
) -> dict:
    """
    Get alert trends over time with SQL aggregation.

    Args:
        interval: Time grouping - "minute" or "hour"
        range_: Time window - "1h", "6h", "24h" (default: 1h)

    Returns:
        List of {time, count} objects
    """
    # Parse range parameter
    range_map = {"1h": 1, "6h": 6, "24h": 24}
    range_hours = range_map.get(range_, 1)

    if interval not in ["minute", "hour"]:
        interval = "minute"

    try:
        db = SessionLocal()
        try:
            data = get_alerts_over_time(
                db=db,
                interval=interval,
                range_hours=range_hours,
            )
            return {
                "success": True,
                "data": data,
                "interval": interval,
                "range": range_,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error("Error fetching alerts over time: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch analytics data",
        )


@router.get("/distribution")
async def event_distribution(range_: str = "24h") -> dict:
    """
    Get event distribution (intrusion/loitering/crowd/weapon) over time window.

    Args:
        range_: Time window - "1h", "6h", "24h" (default: 24h)

    Returns:
        Dict with event type counts
    """
    range_map = {"1h": 1, "6h": 6, "24h": 24}
    range_hours = range_map.get(range_, 24)

    try:
        db = SessionLocal()
        try:
            data = get_event_distribution(
                db=db,
                range_hours=range_hours,
            )
            return {
                "success": True,
                "data": data,
                "range": range_,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error("Error fetching event distribution: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch distribution data",
        )


@router.get("/summary")
async def alert_summary(range_: str = "24h") -> dict:
    """
    Get summary metrics (total, by type) over time window.

    Args:
        range_: Time window - "1h", "6h", "24h" (default: 24h)

    Returns:
        Dict with total, intrusion, loitering, crowd, and weapon counts
    """
    range_map = {"1h": 1, "6h": 6, "24h": 24}
    range_hours = range_map.get(range_, 24)

    try:
        db = SessionLocal()
        try:
            data = get_alert_summary(
                db=db,
                range_hours=range_hours,
            )
            return {
                "success": True,
                "data": data,
                "range": range_,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error("Error fetching alert summary: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch summary data",
        )


@router.get("/recent")
async def recent_alerts(limit: int = 20, range_: str = "24h") -> dict:
    """
    Get recent alerts for activity feed.

    Args:
        limit: Number of recent alerts to return (default: 20)

    Returns:
        List of recent alert records
    """
    if limit < 1 or limit > 100:
        limit = 20

    range_map = {"1h": 1, "6h": 6, "24h": 24}
    range_hours = range_map.get(range_, 24)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=range_hours)

    try:
        db = SessionLocal()
        try:
            rows = (
                db.query(AlertRow)
                .filter(AlertRow.timestamp >= cutoff)
                .order_by(AlertRow.timestamp.desc())
                .limit(limit)
                .all()
            )
            alerts = []
            for row in rows:
                metadata = row.metadata_ or {}
                snapshot_path = str(getattr(row, "snapshot_path", "") or "")
                snapshot_filename = extract_snapshot_filename(snapshot_path)
                timestamp = getattr(row, "timestamp", None)
                alerts.append(
                    {
                        "id": row.id,
                        "event_type": row.event_type,
                        "zone": row.zone or "Unknown",
                        "timestamp": timestamp.isoformat()
                        if timestamp is not None
                        else "",
                        "track_id": row.track_id,
                        "snapshot_path": snapshot_path,
                        "snapshot_filename": snapshot_filename,
                        "snapshot_url": build_snapshot_url(snapshot_filename),
                        "threat_score": int(metadata.get("threat_score", 0)),
                        "threat_level": str(metadata.get("threat_level", "LOW")),
                    }
                )
            return {
                "success": True,
                "data": alerts,
                "count": len(alerts),
                "range": range_,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error("Error fetching recent alerts: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch recent alerts",
        )


@router.get("/threat")
async def threat_metrics(range_: str = "24h", limit: int = 5) -> dict:
    """
    Get threat intelligence metrics for a time window.

    Returns:
        - threat level distribution
        - average threat score
        - peak threat score
        - peak threat events
    """
    range_map = {"1h": 1, "6h": 6, "24h": 24}
    range_hours = range_map.get(range_, 24)
    if limit < 1 or limit > 50:
        limit = 5

    try:
        db = SessionLocal()
        try:
            data = get_threat_metrics(
                db=db,
                range_hours=range_hours,
                peak_limit=limit,
            )
            return {
                "success": True,
                "data": data,
                "range": range_,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error("Error fetching threat metrics: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch threat metrics",
        )
