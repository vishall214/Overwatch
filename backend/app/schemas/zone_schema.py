"""
OVERWATCH — Zone API Schemas
================================
Pydantic schemas for zone-related API requests and responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ZoneCreate(BaseModel):
    """Schema for creating a new zone."""

    type: str
    x: float
    y: float
    width: float
    height: float
    name: Optional[str] = None
    camera_id: str = "default"


class ZoneResponse(BaseModel):
    """Schema for a single zone record."""

    id: int
    name: Optional[str] = None
    type: str
    x: float
    y: float
    width: float
    height: float
    camera_id: str = "default"
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class ZoneListResponse(BaseModel):
    """Schema for a list of zones."""

    zones: list[ZoneResponse] = []
    total: int = 0
