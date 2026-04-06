"""
OVERWATCH — Zone API Schemas
================================
Pydantic schemas for zone-related API requests and responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ZoneCreate(BaseModel):
    """Schema for creating a new zone."""

    type: str
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    width: float = Field(..., gt=0.0, le=1.0)
    height: float = Field(..., gt=0.0, le=1.0)
    name: Optional[str] = None
    camera_id: str = "default"

    @model_validator(mode="after")
    def validate_zone_bounds(self) -> "ZoneCreate":
        """Ensure zone rectangle remains within normalized [0, 1] frame bounds."""
        if self.x + self.width > 1.0:
            raise ValueError("Zone width exceeds frame bounds: x + width must be <= 1.0")
        if self.y + self.height > 1.0:
            raise ValueError("Zone height exceeds frame bounds: y + height must be <= 1.0")
        return self


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
