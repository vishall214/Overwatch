"""
OVERWATCH — Geometry Utility Functions
=========================================
Helper functions for geometric operations used in
zone detection, bounding box math, and spatial analysis.
"""

from typing import Optional


def point_in_polygon(
    point: tuple[float, float],
    polygon: list[tuple[float, float]],
) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.

    Args:
        point: (x, y) coordinate to test.
        polygon: List of (x, y) vertices defining the polygon.

    Returns:
        bool: True if the point is inside the polygon.
    """
    x, y = point
    n = len(polygon)
    inside = False

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i

    return inside


def bbox_center(bbox: list[float]) -> tuple[float, float]:
    """
    Calculate the center point of a bounding box.

    Args:
        bbox: Bounding box as [x1, y1, x2, y2].

    Returns:
        tuple: (center_x, center_y) coordinates.
    """
    return (
        (bbox[0] + bbox[2]) / 2.0,
        (bbox[1] + bbox[3]) / 2.0,
    )


def bbox_bottom_center(bbox: list[float]) -> tuple[float, float]:
    """
    Calculate the bottom-center point of a bounding box.

    Useful for determining where a person is "standing" in the frame.

    Args:
        bbox: Bounding box as [x1, y1, x2, y2].

    Returns:
        tuple: (center_x, bottom_y) coordinates.
    """
    return (
        (bbox[0] + bbox[2]) / 2.0,
        bbox[3],
    )


def bbox_area(bbox: list[float]) -> float:
    """
    Calculate the area of a bounding box.

    Args:
        bbox: Bounding box as [x1, y1, x2, y2].

    Returns:
        float: Area in pixels squared.
    """
    width = max(0.0, bbox[2] - bbox[0])
    height = max(0.0, bbox[3] - bbox[1])
    return width * height


def bbox_iou(bbox_a: list[float], bbox_b: list[float]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.

    Args:
        bbox_a: First bounding box [x1, y1, x2, y2].
        bbox_b: Second bounding box [x1, y1, x2, y2].

    Returns:
        float: IoU value between 0.0 and 1.0.
    """
    # Intersection coordinates
    x1 = max(bbox_a[0], bbox_b[0])
    y1 = max(bbox_a[1], bbox_b[1])
    x2 = min(bbox_a[2], bbox_b[2])
    y2 = min(bbox_a[3], bbox_b[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)

    area_a = bbox_area(bbox_a)
    area_b = bbox_area(bbox_b)

    union = area_a + area_b - intersection

    if union <= 0:
        return 0.0

    return intersection / union
