"""
OVERWATCH — Object Detection Service
=======================================
Wraps YOLOv8 for object detection on video frames.
CPU-only inference with configurable confidence and class filters.

Includes a separate weapon detection model for dangerous object
identification (knife, gun) without modifying existing YOLO logic.
"""

import logging
from typing import Optional

import torch
import numpy as np

# Patch torch.load for PyTorch 2.10+ compatibility with ultralytics
# checkpoints (they require weights_only=False for full deserialization)
_orig_torch_load = torch.load
def _safe_torch_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_torch_load(*args, **kwargs)
torch.load = _safe_torch_load

from ultralytics import YOLO

from app.config import Settings
from app.models.detection import Detection, DetectionResult

logger = logging.getLogger(__name__)


class DetectionService:
    """
    Performs object detection on frames using YOLOv8.

    Loads the YOLOv8 model once and runs inference on each
    frame passed to the detect() method. CPU-only.

    Optionally loads a separate weapon detection model for
    identifying dangerous objects (knife, gun).

    Attributes:
        _settings: Application configuration.
        _model: Loaded YOLO model instance.
        _is_loaded: Whether the model has been loaded.
        _weapon_model: Loaded weapon detection YOLO model.
        _weapon_loaded: Whether the weapon model has been loaded.
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
        self._weapon_model: Optional[YOLO] = None
        self._weapon_loaded: bool = False

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

    def load_weapon_model(self) -> bool:
        """
        Load the weapon detection YOLO model into memory.

        This is a separate model from the main YOLOv8 detector,
        trained specifically for dangerous objects (knife, gun).
        Fails gracefully if the model file is not found.

        Returns:
            bool: True if the weapon model loaded successfully.
        """
        if not self._settings.enable_weapon_detection:
            logger.info("Weapon detection disabled in settings")
            return False

        try:
            model_path = self._settings.weapon_model
            logger.info("Loading weapon detection model: %s", model_path)
            self._weapon_model = YOLO(model_path)
            self._weapon_model.to(self._settings.detection_device)
            self._weapon_loaded = True
            logger.info(
                "Weapon detection model loaded successfully (device: %s, classes: %s)",
                self._settings.detection_device,
                list(self._weapon_model.names.values()) if self._weapon_model.names else "unknown",
            )
            return True
        except Exception:
            logger.warning(
                "Failed to load weapon detection model from '%s' — "
                "weapon detection will be unavailable",
                self._settings.weapon_model,
            )
            self._weapon_loaded = False
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
        detection_classes = (
            self._settings.detection_classes
            if self._settings.detection_classes
            else None
        )
        results = self._model(
            frame,
            conf=self._settings.detection_confidence,
            iou=self._settings.detection_iou_threshold,
            max_det=self._settings.detection_max_det,
            imgsz=self._settings.detection_img_size,
            device=self._settings.detection_device,
            classes=detection_classes,
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

    def detect_weapons(self, frame: np.ndarray) -> list[Detection]:
        """
        Run weapon detection on a single frame using the weapon model.

        Uses a separate YOLO model trained for dangerous objects.
        Only returns detections meeting the weapon confidence threshold.

        Args:
            frame: Input BGR frame as numpy array.

        Returns:
            list[Detection]: List of weapon Detection objects with
                            detection_type="weapon".
        """
        if not self._weapon_loaded or self._weapon_model is None:
            return []

        try:
            # Pass weapon_classes to YOLO so non-weapon detections are
            # discarded at inference time (more efficient than post-filter)
            weapon_classes = self._settings.weapon_classes if self._settings.weapon_classes else None
            results = self._weapon_model(
                frame,
                conf=self._settings.weapon_confidence,
                imgsz=self._settings.detection_img_size,
                device=self._settings.detection_device,
                classes=weapon_classes,
                augment=False,
                verbose=False,
            )

            detections: list[Detection] = []
            result = results[0]

            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes
                for i in range(len(boxes)):
                    xyxy = boxes.xyxy[i].cpu().numpy()
                    conf = float(boxes.conf[i].cpu().numpy())
                    cls_id = int(boxes.cls[i].cpu().numpy())
                    cls_name = self._weapon_model.names.get(cls_id, str(cls_id))

                    # COCO often flips knife/scissors by angle/location.
                    # Keep recall high but normalize to a single "knife" label.
                    if cls_id == 76:
                        cls_id = 43
                        cls_name = "knife"

                    if conf >= self._settings.weapon_confidence:
                        detection = Detection(
                            bbox=[float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                            confidence=conf,
                            class_id=cls_id,
                            class_name=cls_name,
                            detection_type="weapon",
                        )
                        detections.append(detection)

            logger.debug("Weapon detection: %d objects found", len(detections))
            return detections

        except Exception:
            logger.exception("Error in weapon detection")
            return []

    @property
    def is_loaded(self) -> bool:
        """Return whether the detection model is loaded."""
        return self._is_loaded

    @property
    def weapon_is_loaded(self) -> bool:
        """Return whether the weapon detection model is loaded."""
        return self._weapon_loaded

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
            "weapon_model": self._settings.weapon_model,
            "weapon_loaded": self._weapon_loaded,
            "weapon_confidence": self._settings.weapon_confidence,
        }
