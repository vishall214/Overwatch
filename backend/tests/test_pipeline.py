import time
from dataclasses import dataclass

import numpy as np

from app.config import Settings
from app.core.event_bus import EventBus
from app.core.queues import FramePacket, PipelineQueues
from app.pipelines.inference_worker import InferenceWorker


@dataclass
class _DetectionResult:
    detections: list
    annotated_frame: np.ndarray


class _StubDetection:
    def __init__(self, class_name: str = "knife", confidence: float = 0.9) -> None:
        self.class_name = class_name
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "class_name": self.class_name,
            "confidence": self.confidence,
            "type": "weapon",
        }


class _StubDetectionService:
    def __init__(self) -> None:
        self.is_loaded = True
        self.weapon_is_loaded = True
        self.weapon_calls = 0

    def detect(self, frame: np.ndarray) -> _DetectionResult:
        return _DetectionResult(detections=[], annotated_frame=frame)

    def detect_weapons(self, frame: np.ndarray) -> list[_StubDetection]:
        self.weapon_calls += 1
        return []


def test_inference_worker_weapon_skip_frame_semantics() -> None:
    settings = Settings(weapon_skip_frames=2)
    queues = PipelineQueues()
    detection_service = _StubDetectionService()
    worker = InferenceWorker(
        settings=settings,
        detection_service=detection_service,  # type: ignore[arg-type]
        queues=queues,
        event_bus=EventBus(),
    )

    worker.start()
    try:
        for frame_index in range(1, 5):
            packet = FramePacket(
                frame=np.zeros((64, 64, 3), dtype=np.uint8),
                frame_index=frame_index,
                timestamp_ns=time.monotonic_ns(),
            )
            queues.frame_queue.put(packet)

        deadline = time.monotonic() + 3.0
        while worker.stats["frames_processed"] < 4 and time.monotonic() < deadline:
            time.sleep(0.01)

        assert worker.stats["frames_processed"] == 4
        assert detection_service.weapon_calls == 2

        packets = []
        while not queues.detection_queue.empty():
            packets.append(queues.detection_queue.get_nowait())

        assert len(packets) == 4
        ran_weapon_frames = [p.frame_index for p in packets if p.weapon_detections is not None]
        skipped_weapon_frames = [p.frame_index for p in packets if p.weapon_detections is None]

        assert ran_weapon_frames == [2, 4]
        assert skipped_weapon_frames == [1, 3]
        assert all(p.weapon_detections == [] for p in packets if p.weapon_detections is not None)
    finally:
        worker.stop()
