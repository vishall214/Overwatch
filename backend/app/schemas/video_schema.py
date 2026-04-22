"""
OVERWATCH — Video Source API Schemas
=======================================
Pydantic schemas for video source switching, demo listing,
and upload endpoints.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SourceSwitchRequest(BaseModel):
    """Request body for POST /video/source."""

    type: str = Field(
        ...,
        description="Source type: 'camera', 'demo', or 'upload'.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Video filename (required for demo sources).",
    )
    category: Optional[str] = Field(
        default=None,
        description="Demo category folder (e.g. 'intrusion').",
    )
    path: Optional[str] = Field(
        default=None,
        description="Path to uploaded video (required for upload sources).",
    )
    module: Optional[
        Literal["intrusion", "loitering", "crowd", "weapon_detection", "weapons"]
    ] = Field(
        default=None,
        description="Module initiating source switch.",
    )


class SourceSwitchResponse(BaseModel):
    """Response for POST /video/source."""

    success: bool = True
    message: str
    source_type: str
    source_name: str


class DemoListResponse(BaseModel):
    """Response for GET /video/demo/list."""

    category: str
    videos: list[str]


class UploadResponse(BaseModel):
    """Response for POST /video/upload."""

    success: bool = True
    message: str
    filename: str
    path: str
    size_mb: float
