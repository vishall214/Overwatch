"""
OVERWATCH — Alert API Schemas
================================
Pydantic schemas for alert-related API requests and responses.

Phase 1: Stub schemas for future use.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AlertResponse(BaseModel):
    """
    Schema for an alert record.

    Attributes:
        id: Unique alert identifier.
        type: Alert type (e.g., 'zone_intrusion', 'loitering').
        severity: Alert severity level.
        message: Human-readable alert description.
        timestamp: When the alert was created.
        acknowledged: Whether the alert has been acknowledged.
    """

    id: int
    type: str
    severity: str = "medium"
    message: str = ""
    timestamp: Optional[datetime] = None
    acknowledged: bool = False


class AlertListResponse(BaseModel):
    """
    Schema for a list of alerts.

    Attributes:
        alerts: List of alert records.
        total: Total number of alerts matching the query.
    """

    alerts: list[AlertResponse] = []
    total: int = 0
