"""
OVERWATCH — Alert API Schemas
================================
Pydantic schemas for alert-related API requests and responses.
"""

from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class AlertResponse(BaseModel):
    """Schema for a single alert record."""

    id: int
    event_type: str
    timestamp: datetime
    track_id: Optional[int] = None
    zone: str = ""
    metadata: dict[str, Any] = {}
    snapshot_path: str = ""
    snapshot_filename: str = ""
    snapshot_url: str = ""
    threat_score: int = 0
    threat_level: str = "LOW"


class AlertListResponse(BaseModel):
    """Schema for a list of alerts."""

    alerts: list[AlertResponse] = []
    total: int = 0
