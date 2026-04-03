"""
OVERWATCH — Detection Domain Models
=======================================
Data classes for object detection results.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Detection:
    """
    Represents a single detected object in a frame.

    Attributes:
        bbox: Bounding box coordinates [x1, y1, x2, y2] in pixels.
        confidence: Detection confidence score (0.0 to 1.0).
        class_id: Integer class ID from the detection model.
        class_name: Human-readable class name.
    """

    bbox: list[float]
    confidence: float
    class_id: int
    class_name: str
    detection_type: str = "object"

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the detection to a dictionary.

        Returns:
            dict: Detection data as a JSON-serializable dictionary.
        """
        return {
            "bbox": self.bbox,
            "confidence": round(self.confidence, 3),
            "class_id": self.class_id,
            "class_name": self.class_name,
            "type": self.detection_type,
        }


@dataclass
class DetectionResult:
    """
    Represents the result of running detection on a single frame.

    Attributes:
        detections: List of Detection objects found in the frame.
        annotated_frame: The frame with bounding boxes drawn on it.
    """

    detections: list[Detection] = field(default_factory=list)
    annotated_frame: np.ndarray = field(default_factory=lambda: np.array([]))

    @property
    def count(self) -> int:
        """Return the number of detections."""
        return len(self.detections)

    @property
    def has_detections(self) -> bool:
        """Return whether any objects were detected."""
        return len(self.detections) > 0
