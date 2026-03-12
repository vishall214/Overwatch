"""
OVERWATCH — Video Processing Pipeline
=========================================
Orchestrates the worker-based video processing pipeline.

Pipeline flow:
    Camera Source
    → CaptureWorker  (thread)  → frame_queue
    → InferenceWorker(thread)  → detection_queue
    → StreamWorker   (thread)  → stream_queue
    → FastAPI MJPEG endpoint

Each stage runs in its own daemon thread communicating
through thread-safe queues.
"""

import asyncio
import logging
from typing import Optional

from app.config import Settings
from app.core.event_bus import EventBus, Event
from app.core.queues import PipelineQueues
from app.services.video_service import VideoService
from app.services.detection_service import DetectionService
from app.services.alert_service import AlertService
from app.services.face.face_service import FaceService
from app.services.module_controller import ModuleController
from app.pipelines.capture_worker import CaptureWorker
from app.pipelines.inference_worker import InferenceWorker
from app.pipelines.tracking_worker import TrackingWorker
from app.pipelines.behavior_worker import BehaviorWorker
from app.pipelines.stream_worker import StreamWorker

logger = logging.getLogger(__name__)


class VideoPipeline:
    """
    Orchestrates the video processing pipeline lifecycle.

    Manages five background worker threads and the shared
    queue infrastructure.  Exposes start/stop/status for the
    camera API routes.

    Attributes:
        _settings: Application configuration.
        _event_bus: Internal event bus for decoupled communication.
        _video_service: Video capture service.
        _detection_service: Object detection service.
        _queues: Thread-safe inter-worker queues.
        _capture_worker: Background frame-capture thread.
        _inference_worker: Background YOLOv8 inference thread.
        _tracking_worker: Background ByteTrack tracking thread.
        _behavior_worker: Background behavior analysis thread.
        _stream_worker: Background JPEG-encoding thread.
        _is_running: Whether the pipeline is actively processing.
    """

    def __init__(
        self,
        settings: Settings,
        event_bus: EventBus,
        video_service: VideoService,
        detection_service: DetectionService,
        queues: PipelineQueues,
        alert_service: Optional[AlertService] = None,
        face_service: Optional[FaceService] = None,
        module_controller: Optional[ModuleController] = None,
    ) -> None:
        """
        Initialize the VideoPipeline.

        Args:
            settings: Application configuration.
            event_bus: Internal event bus for publishing pipeline events.
            video_service: Service for capturing video frames.
            detection_service: Service for running object detection.
            queues: Thread-safe inter-worker queues.
            alert_service: Optional alert service for behavior alerts.
            face_service: Optional face recognition service.
            module_controller: Optional analytics module controller.
        """
        self._settings: Settings = settings
        self._event_bus: EventBus = event_bus
        self._video_service: VideoService = video_service
        self._detection_service: DetectionService = detection_service
        self._queues: PipelineQueues = queues
        self._alert_service: Optional[AlertService] = alert_service
        self._face_service: Optional[FaceService] = face_service
        self._module_controller: Optional[ModuleController] = module_controller

        self._capture_worker: Optional[CaptureWorker] = None
        self._inference_worker: Optional[InferenceWorker] = None
        self._tracking_worker: Optional[TrackingWorker] = None
        self._behavior_worker: Optional[BehaviorWorker] = None
        self._stream_worker: Optional[StreamWorker] = None

        self._is_running: bool = False

    async def start(self, source: Optional[str] = None) -> bool:
        """
        Start the video processing pipeline.

        Opens the video source, loads the detection model, and
        starts three background worker threads.

        Args:
            source: Optional video source override.

        Returns:
            bool: True if the pipeline started successfully.
        """
        if self._is_running:
            logger.warning("Pipeline already running")
            return False

        resolved_source = source or self._settings.video_source
        logger.info("Starting video pipeline (source=%s)", resolved_source)

        loop = asyncio.get_running_loop()

        # ── Open video source (blocking I/O → executor) ───────
        opened = await loop.run_in_executor(
            None, self._video_service.start, source,
        )
        if not opened:
            logger.error("Failed to open video source during pipeline start (source=%s)", resolved_source)
            return False

        # ── Load detection model (blocking I/O → executor) ────
        if not self._detection_service.is_loaded:
            loaded = await loop.run_in_executor(
                None, self._detection_service.load_model,
            )
            if not loaded:
                logger.error("Failed to load detection model during pipeline start")
                self._video_service.stop()
                return False

        # ── Load face recognition model (blocking I/O → executor) ──
        if self._face_service is not None and not self._face_service.is_loaded:
            face_ok = await loop.run_in_executor(
                None, self._face_service.load_model,
            )
            if not face_ok:
                logger.warning("Face recognition model failed to load — running without face ID")

        # ── Clear stale data from previous run ──────────────────
        self._queues.clear_all()

        # ── Create workers ──────────────────────────────────────
        self._capture_worker = CaptureWorker(
            settings=self._settings,
            video_service=self._video_service,
            queues=self._queues,
        )
        self._inference_worker = InferenceWorker(
            settings=self._settings,
            detection_service=self._detection_service,
            queues=self._queues,
            event_bus=self._event_bus,
        )
        self._tracking_worker = TrackingWorker(
            settings=self._settings,
            queues=self._queues,
        )
        self._behavior_worker = BehaviorWorker(
            settings=self._settings,
            queues=self._queues,
            event_bus=self._event_bus,
            alert_service=self._alert_service,
            face_service=self._face_service,
            module_controller=self._module_controller,
        )
        self._stream_worker = StreamWorker(
            settings=self._settings,
            queues=self._queues,
        )

        # ── Start workers (order matters) ───────────────────────
        self._capture_worker.start()
        self._inference_worker.start()
        self._tracking_worker.start()
        self._behavior_worker.start()
        self._stream_worker.start()

        self._is_running = True

        await self._event_bus.publish(Event(
            type="PipelineStarted",
            data={"source": source or self._settings.video_source},
        ))

        logger.info("Video pipeline started (5 workers, source=%s)", resolved_source)
        return True

    async def stop(self) -> None:
        """
        Stop the pipeline and release all resources.

        Stops workers in reverse order, drains queues, and
        releases the video source.
        """
        if not self._is_running:
            return

        self._is_running = False

        loop = asyncio.get_running_loop()

        # Stop workers in reverse order (thread.join → executor)
        if self._stream_worker is not None:
            await loop.run_in_executor(None, self._stream_worker.stop)
        if self._behavior_worker is not None:
            await loop.run_in_executor(None, self._behavior_worker.stop)
        if self._tracking_worker is not None:
            await loop.run_in_executor(None, self._tracking_worker.stop)
        if self._inference_worker is not None:
            await loop.run_in_executor(None, self._inference_worker.stop)
        if self._capture_worker is not None:
            await loop.run_in_executor(None, self._capture_worker.stop)

        # Drain queues
        self._queues.clear_all()

        # Release camera
        self._video_service.stop()

        frames_processed = (
            self._capture_worker.frame_count if self._capture_worker else 0
        )

        await self._event_bus.publish(Event(
            type="PipelineStopped",
            data={"frames_processed": frames_processed},
        ))

        logger.info("Video pipeline stopped (processed %d frames)", frames_processed)

    @property
    def is_running(self) -> bool:
        """Return whether the pipeline is actively processing."""
        return self._is_running

    @property
    def stats(self) -> dict:
        """
        Return current pipeline statistics.

        Returns:
            dict: Pipeline stats including worker state and queue levels.
        """
        capture_stats = {
            "is_running": False,
            "frames_captured": 0,
            "frames_dropped": 0,
            "avg_capture_ms": 0.0,
            "queue_depth": 0,
        }
        inference_stats = {
            "is_running": False,
            "frames_processed": 0,
            "avg_inference_ms": 0.0,
            "avg_input_age_ms": 0.0,
            "frames_dropped": 0,
            "skip_frames": 0,
        }
        tracking_stats = {
            "is_running": False,
            "frames_tracked": 0,
            "avg_tracking_ms": 0.0,
            "avg_input_age_ms": 0.0,
            "frames_dropped": 0,
        }
        behavior_stats = {
            "is_running": False,
            "frames_analyzed": 0,
            "avg_behavior_ms": 0.0,
            "avg_input_age_ms": 0.0,
            "frames_dropped": 0,
            "face_queue_depth": 0,
            "pending_face_tracks": 0,
        }
        stream_stats = {
            "is_running": False,
            "frames_encoded": 0,
            "avg_stream_ms": 0.0,
            "avg_total_latency_ms": 0.0,
            "frames_dropped": 0,
        }

        if self._capture_worker is not None:
            capture_stats = self._capture_worker.stats

        if self._inference_worker is not None:
            inference_stats = self._inference_worker.stats

        if self._tracking_worker is not None:
            tracking_stats = self._tracking_worker.stats

        if self._behavior_worker is not None:
            behavior_stats = self._behavior_worker.stats

        if self._stream_worker is not None:
            stream_stats = self._stream_worker.stats

        return {
            "is_running": self._is_running,
            "source": self._video_service.source_info,
            "detection": self._detection_service.model_info,
            "capture_worker": capture_stats,
            "inference_worker": inference_stats,
            "tracking_worker": tracking_stats,
            "behavior_worker": behavior_stats,
            "stream_worker": stream_stats,
            "queues": self._queues.stats,
        }
