"""
OVERWATCH — Reports API Routes
==============================
Endpoints for listing, generating, and downloading analytics reports.
"""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.security import get_current_user
from app.services.report_scheduler import ReportScheduler
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_user)],
)

_report_service: Optional[ReportService] = None
_report_scheduler: Optional[ReportScheduler] = None


def init_report_routes(
    report_service: ReportService,
    scheduler: Optional[ReportScheduler] = None,
) -> None:
    """Inject report service/scheduler singletons at startup."""
    global _report_service, _report_scheduler
    _report_service = report_service
    _report_scheduler = scheduler


def _get_report_service() -> ReportService:
    if _report_service is None:
        raise HTTPException(status_code=503, detail="Report service not initialized")
    return _report_service


@router.get("")
async def list_reports(limit: int = 30) -> dict:
    """List available reports, newest first."""
    service = _get_report_service()
    safe_limit = max(1, min(limit, 200))
    data = service.list_reports(limit=safe_limit)
    return {
        "success": True,
        "data": data,
        "count": len(data),
    }


@router.get("/scheduler")
async def get_scheduler_status() -> dict:
    """Return scheduler/email status for the reports system."""
    if _report_scheduler is None:
        return {
            "success": True,
            "data": {
                "enabled": False,
                "running": False,
                "daily_time_utc": "",
                "weekly_day_utc": 0,
                "poll_seconds": 0,
                "last_daily_date": "",
                "last_weekly_key": "",
                "email_enabled": False,
                "email_recipients_count": 0,
            },
        }

    return {
        "success": True,
        "data": _report_scheduler.get_status(),
    }


@router.post("/generate")
async def generate_report(period: Literal["daily", "weekly"] = Query(default="daily")) -> dict:
    """Manually trigger generation of a daily or weekly report."""
    service = _get_report_service()
    try:
        artifact = service.generate_report(period=period, trigger="manual")
        return {
            "success": True,
            "data": artifact,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/{report_id}")
async def get_report(report_id: str) -> dict:
    """Return full report JSON payload."""
    service = _get_report_service()
    try:
        payload = service.get_report(report_id)
        return {
            "success": True,
            "data": payload,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{report_id}/download")
async def download_report(report_id: str, format_: Literal["json", "csv"] = Query(default="json", alias="format")):
    """Download a report artifact as JSON or CSV."""
    service = _get_report_service()
    try:
        path = service.get_report_file_path(report_id, format_=format_)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report file not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    media_type = "application/json" if format_ == "json" else "text/csv"
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name,
    )
