"""
OVERWATCH — Video Source API Schemas
=======================================
Pydantic schemas for video source switching, demo listing,
and upload endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional


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
    module: Optional[str] = Field(
        default=None,
        description="Module initiating source switch (intrusion/loitering/crowd).",
    )


class SourceSwitchResponse(BaseModel):
    """Response for POST /video/source."""

    message: str
    source_type: str
    source_name: str


class DemoListResponse(BaseModel):
    """Response for GET /video/demo/list."""

    category: str
    videos: list[str]


class UploadResponse(BaseModel):
    """Response for POST /video/upload."""

    message: str
    filename: str
    path: str
