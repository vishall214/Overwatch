"""
OVERWATCH — Image Utility Functions
=======================================
Helper functions for frame preprocessing and image operations.
"""

import cv2
import numpy as np


def resize_frame(
    frame: np.ndarray,
    max_dimension: int = 640,
) -> np.ndarray:
    """
    Resize a frame so its largest dimension does not exceed max_dimension.

    Maintains aspect ratio. Only downsizes; never upsizes.

    Args:
        frame: Input BGR frame as numpy array.
        max_dimension: Maximum allowed pixel dimension.

    Returns:
        np.ndarray: Resized frame (or original if already within limits).
    """
    h, w = frame.shape[:2]

    if max(h, w) <= max_dimension:
        return frame

    scale = max_dimension / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)


def frame_to_jpeg(frame: np.ndarray, quality: int = 80) -> bytes | None:
    """
    Encode a BGR frame as JPEG bytes.

    Args:
        frame: Input BGR frame as numpy array.
        quality: JPEG compression quality (1-100).

    Returns:
        bytes or None: JPEG-encoded bytes, or None if encoding fails.
    """
    params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    success, buffer = cv2.imencode(".jpg", frame, params)

    if not success:
        return None

    return buffer.tobytes()


def draw_text_overlay(
    frame: np.ndarray,
    text: str,
    position: tuple[int, int] = (10, 30),
    color: tuple[int, int, int] = (0, 255, 0),
    font_scale: float = 0.7,
    thickness: int = 2,
) -> np.ndarray:
    """
    Draw a text overlay on a frame with a dark background for readability.

    Args:
        frame: Input BGR frame (modified in place).
        text: Text string to draw.
        position: Top-left position (x, y) for the text.
        color: BGR color tuple for the text.
        font_scale: Font size scale factor.
        thickness: Line thickness of the text.

    Returns:
        np.ndarray: Frame with text drawn on it.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]

    # Draw background rectangle
    x, y = position
    cv2.rectangle(
        frame,
        (x - 2, y - text_size[1] - 6),
        (x + text_size[0] + 2, y + 4),
        (0, 0, 0),
        cv2.FILLED,
    )

    # Draw text
    cv2.putText(frame, text, position, font, font_scale, color, thickness)
    return frame
