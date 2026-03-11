"""
OVERWATCH — Object Detection Service
=======================================
Wraps YOLOv8 for object detection on video frames.
CPU-only inference with configurable confidence and class filters.
"""

import logging
from typing import Optional

import numpy as np
from ultralytics import YOLO

from app.config import Settings
from app.models.detection import Detection, DetectionResult

logger = logging.getLogger(__name__)


class DetectionService:
    """
    Performs object detection on frames using YOLOv8.

    Loads the YOLOv8 model once and runs inference on each
    frame passed to the detect() method. CPU-only.

    Attributes:
        _settings: Application configuration.
        _model: Loaded YOLO model instance.
        _is_loaded: Whether the model has been loaded.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the DetectionService.

        Args:
            settings: Application configuration with detection parameters.
        """
        self._settings: Settings = settings
        self._model: Optional[YOLO] = None
        self._is_loaded: bool = False

    def load_model(self) -> bool:
        """
        Load the YOLOv8 model into memory.

        Downloads the model weights if not present locally.
        Forces CPU device for inference.

        Returns:
            bool: True if the model loaded successfully.
        """
        try:
            model_path = self._settings.detection_model
            logger.info("Loading YOLOv8 model: %s", model_path)
            self._model = YOLO(model_path)
            # Force CPU inference
            self._model.to(self._settings.detection_device)
            self._is_loaded = True
            logger.info("YOLOv8 model loaded successfully (device: %s)", self._settings.detection_device)
            return True
        except Exception:
            logger.exception("Failed to load YOLOv8 model")
            self._is_loaded = False
            return False

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Run object detection on a single frame.

        Args:
            frame: Input BGR frame as numpy array.

        Returns:
            DetectionResult: Contains list of Detection objects and
                            the annotated frame with bounding boxes drawn.
        """
        if not self._is_loaded or self._model is None:
            logger.warning("Detection model not loaded, returning empty result")
            return DetectionResult(detections=[], annotated_frame=frame)

        # Run inference
        results = self._model(
            frame,
            conf=self._settings.detection_confidence,
            iou=self._settings.detection_iou_threshold,
            max_det=self._settings.detection_max_det,
            imgsz=self._settings.detection_img_size,
            device=self._settings.detection_device,
            classes=self._settings.detection_classes,
            verbose=False,
        )

        detections: list[Detection] = []
        result = results[0]

        # Parse detections
        if result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes
            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].cpu().numpy()
                conf = float(boxes.conf[i].cpu().numpy())
                cls_id = int(boxes.cls[i].cpu().numpy())
                cls_name = self._model.names.get(cls_id, str(cls_id))

                detection = Detection(
                    bbox=[float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                    confidence=conf,
                    class_id=cls_id,
                    class_name=cls_name,
                )
                detections.append(detection)

        logger.debug("Detected %d objects", len(detections))

        return DetectionResult(
            detections=detections,
            annotated_frame=frame,
        )

    @property
    def is_loaded(self) -> bool:
        """Return whether the detection model is loaded."""
        return self._is_loaded

    @property
    def model_info(self) -> dict:
        """
        Return metadata about the loaded detection model.

        Returns:
            dict: Model information including name and device.
        """
        return {
            "model": self._settings.detection_model,
            "loaded": self._is_loaded,
            "device": self._settings.detection_device,
            "confidence_threshold": self._settings.detection_confidence,
            "classes": self._settings.detection_classes,
        }
