"""
OVERWATCH — Tracking Domain Models
======================================
Data classes for object tracking state.

Phase 2 implementation. Models defined now to prevent
refactoring when ByteTrack tracking is added.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class TrackState(Enum):
    """
    Lifecycle state of a tracked object.

    Attributes:
        TENTATIVE: Track recently created, not yet confirmed.
        CONFIRMED: Track has been matched across enough frames.
        LOST: Track has not been matched for several frames.
        DELETED: Track has been permanently removed.
    """

    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    LOST = "lost"
    DELETED = "deleted"


@dataclass
class TrackedObject:
    """
    Represents a single tracked object at a specific frame.

    Captures the current state of a tracked entity including
    its bounding box, class, and tracking metadata.

    Attributes:
        track_id: Unique persistent track identifier.
        bbox: Current bounding box [x1, y1, x2, y2] in pixels.
        confidence: Detection confidence for the current frame.
        class_id: Integer class ID from the detection model.
        class_name: Human-readable class name.
        state: Current lifecycle state of the track.
        velocity: Estimated velocity (dx, dy) in pixels per frame.
        age: Number of frames since the track was created.
        hits: Number of frames where the track was matched.
        time_since_update: Frames since last successful match.
    """

    track_id: int
    bbox: list[float]
    confidence: float
    class_id: int
    class_name: str
    state: TrackState = TrackState.TENTATIVE
    velocity: tuple[float, float] = (0.0, 0.0)
    age: int = 0
    hits: int = 0
    time_since_update: int = 0

    @property
    def center(self) -> tuple[float, float]:
        """
        Calculate center point of the bounding box.

        Returns:
            tuple: (center_x, center_y) coordinates.
        """
        return (
            (self.bbox[0] + self.bbox[2]) / 2.0,
            (self.bbox[1] + self.bbox[3]) / 2.0,
        )

    @property
    def bottom_center(self) -> tuple[float, float]:
        """
        Calculate bottom-center point (foot position estimate).

        Returns:
            tuple: (center_x, bottom_y) coordinates.
        """
        return (
            (self.bbox[0] + self.bbox[2]) / 2.0,
            self.bbox[3],
        )

    @property
    def is_confirmed(self) -> bool:
        """Return whether the track is in confirmed state."""
        return self.state == TrackState.CONFIRMED

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the tracked object to a dictionary.

        Returns:
            dict: JSON-serializable track data.
        """
        return {
            "track_id": self.track_id,
            "bbox": self.bbox,
            "confidence": round(self.confidence, 3),
            "class_id": self.class_id,
            "class_name": self.class_name,
            "state": self.state.value,
            "velocity": self.velocity,
            "center": self.center,
            "age": self.age,
            "hits": self.hits,
        }


@dataclass
class Track:
    """
    Represents the full history and state of a tracked entity.

    Maintains the complete trajectory of a tracked object across
    frames, used by the behavior engine for loitering, speed,
    and zone analysis.

    Attributes:
        track_id: Unique persistent track identifier.
        class_id: Detection class that initiated the track.
        class_name: Human-readable class name.
        state: Current lifecycle state.
        history: List of (frame_index, bbox) tuples for trajectory.
        first_seen: Frame index when track was created.
        last_seen: Frame index of last match.
        total_hits: Total frames with successful matches.
    """

    track_id: int
    class_id: int
    class_name: str
    state: TrackState = TrackState.TENTATIVE
    history: list[tuple[int, list[float]]] = field(default_factory=list)
    first_seen: int = 0
    last_seen: int = 0
    total_hits: int = 0

    def add_observation(self, frame_index: int, bbox: list[float]) -> None:
        """
        Record a new observation for this track.

        Args:
            frame_index: Current frame index.
            bbox: Bounding box [x1, y1, x2, y2] at this frame.
        """
        self.history.append((frame_index, bbox))
        self.last_seen = frame_index
        self.total_hits += 1

    @property
    def duration_frames(self) -> int:
        """Return the number of frames this track has existed."""
        return self.last_seen - self.first_seen

    @property
    def latest_bbox(self) -> list[float] | None:
        """
        Return the most recent bounding box.

        Returns:
            list[float] or None: Latest bbox, or None if no history.
        """
        if not self.history:
            return None
        return self.history[-1][1]

    @property
    def latest_center(self) -> tuple[float, float] | None:
        """
        Return the center of the most recent bounding box.

        Returns:
            tuple or None: (center_x, center_y), or None if no history.
        """
        bbox = self.latest_bbox
        if bbox is None:
            return None
        return (
            (bbox[0] + bbox[2]) / 2.0,
            (bbox[1] + bbox[3]) / 2.0,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the track to a dictionary (excluding full history).

        Returns:
            dict: JSON-serializable track summary.
        """
        return {
            "track_id": self.track_id,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "state": self.state.value,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "total_hits": self.total_hits,
            "duration_frames": self.duration_frames,
            "latest_bbox": self.latest_bbox,
        }
