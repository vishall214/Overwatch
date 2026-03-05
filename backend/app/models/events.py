"""
OVERWATCH — Domain Event Models
===================================
Typed dataclass definitions for all internal system events
used by the event-driven architecture.

Events flow through the EventBus to decouple services:

    FrameCapturedEvent → DetectionService
    DetectionEvent     → TrackingService (Phase 2)
    TrackingEvent      → BehaviorEngine (Phase 2)
    IntrusionEvent     → AlertService (Phase 2)
    AlertEvent         → Database + API (Phase 3)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.models.detection import Detection


@dataclass
class FrameCapturedEvent:
    """
    Published when a new frame is captured from the video source.

    Attributes:
        frame: Raw BGR frame as numpy array.
        frame_index: Sequential frame counter.
        source: Video source identifier.
        timestamp: UTC time when the frame was captured.
    """

    frame: np.ndarray
    frame_index: int
    source: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Return the event type identifier string."""
        return "FrameCaptured"


@dataclass
class DetectionEvent:
    """
    Published when object detection completes on a frame.

    Attributes:
        frame: Original BGR frame.
        annotated_frame: Frame with bounding boxes drawn.
        detections: List of Detection objects found.
        frame_index: Sequential frame counter.
        timestamp: UTC time when detection completed.
    """

    frame: np.ndarray
    annotated_frame: np.ndarray
    detections: list[Detection]
    frame_index: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Return the event type identifier string."""
        return "DetectionComplete"

    @property
    def detection_count(self) -> int:
        """Return the number of detections."""
        return len(self.detections)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize event metadata to a dictionary (excludes frame data).

        Returns:
            dict: JSON-serializable event data.
        """
        return {
            "event_type": self.event_type,
            "frame_index": self.frame_index,
            "detection_count": self.detection_count,
            "detections": [d.to_dict() for d in self.detections],
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TrackingEvent:
    """
    Published when object tracking updates are computed.

    Phase 2 implementation. Defined now to avoid refactors.

    Attributes:
        frame: Original BGR frame.
        annotated_frame: Frame with tracking overlays.
        tracks: List of active track dictionaries.
        frame_index: Sequential frame counter.
        timestamp: UTC time when tracking completed.
    """

    frame: np.ndarray
    annotated_frame: np.ndarray
    tracks: list[dict[str, Any]]
    frame_index: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Return the event type identifier string."""
        return "TrackingComplete"

    @property
    def active_track_count(self) -> int:
        """Return the number of active tracks."""
        return len(self.tracks)


@dataclass
class IntrusionEvent:
    """
    Published when a tracked person enters a restricted zone.

    Phase 2 implementation. Defined now to avoid refactors.

    Attributes:
        track_id: ID of the track that triggered the intrusion.
        zone_id: Identifier of the restricted zone violated.
        zone_name: Human-readable zone name.
        bbox: Bounding box of the intruding object [x1, y1, x2, y2].
        frame_index: Frame where the intrusion was detected.
        timestamp: UTC time of detection.
    """

    track_id: int
    zone_id: str
    zone_name: str
    bbox: list[float]
    frame_index: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Return the event type identifier string."""
        return "IntrusionDetected"

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to a JSON-serializable dictionary.

        Returns:
            dict: Event data.
        """
        return {
            "event_type": self.event_type,
            "track_id": self.track_id,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "bbox": self.bbox,
            "frame_index": self.frame_index,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class LoiteringEvent:
    """
    Published when a tracked person loiters in a zone beyond threshold.

    Phase 2 implementation. Defined now to avoid refactors.

    Attributes:
        track_id: ID of the loitering track.
        zone_id: Identifier of the zone.
        zone_name: Human-readable zone name.
        duration_seconds: How long the person has been in the zone.
        bbox: Current bounding box [x1, y1, x2, y2].
        frame_index: Frame where loitering was confirmed.
        timestamp: UTC time of detection.
    """

    track_id: int
    zone_id: str
    zone_name: str
    duration_seconds: float
    bbox: list[float]
    frame_index: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Return the event type identifier string."""
        return "LoiteringDetected"

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to a JSON-serializable dictionary.

        Returns:
            dict: Event data.
        """
        return {
            "event_type": self.event_type,
            "track_id": self.track_id,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "duration_seconds": round(self.duration_seconds, 1),
            "bbox": self.bbox,
            "frame_index": self.frame_index,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AlertEvent:
    """
    Published when a security alert is generated.

    Phase 3 implementation for database logging.
    Defined now to avoid refactors.

    Attributes:
        alert_type: Type of alert (intrusion, loitering, etc.).
        severity: Alert severity (low, medium, high, critical).
        message: Human-readable description.
        source_event_type: The event type that triggered the alert.
        metadata: Additional context from the triggering event.
        frame_index: Frame where the alert was generated.
        timestamp: UTC time of the alert.
    """

    alert_type: str
    severity: str
    message: str
    source_event_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    frame_index: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Return the event type identifier string."""
        return "AlertCreated"

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to a JSON-serializable dictionary.

        Returns:
            dict: Alert event data.
        """
        return {
            "event_type": self.event_type,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "source_event_type": self.source_event_type,
            "metadata": self.metadata,
            "frame_index": self.frame_index,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PipelineStartedEvent:
    """
    Published when the video processing pipeline starts.

    Attributes:
        source: Video source identifier.
        timestamp: UTC time of startup.
    """

    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Return the event type identifier string."""
        return "PipelineStarted"


@dataclass
class PipelineStoppedEvent:
    """
    Published when the video processing pipeline stops.

    Attributes:
        frames_processed: Total frames processed during the run.
        timestamp: UTC time of shutdown.
    """

    frames_processed: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Return the event type identifier string."""
        return "PipelineStopped"
