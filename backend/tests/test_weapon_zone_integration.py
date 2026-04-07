import numpy as np

from app.config import Settings
from app.core.event_bus import EventBus
from app.core.queues import PipelineQueues
from app.pipelines.behavior_worker import BehaviorWorker


class StubAlertService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create_alert(self, **kwargs):
        self.calls.append(kwargs)
        return kwargs


def make_worker() -> tuple[BehaviorWorker, StubAlertService]:
    settings = Settings()
    alert_service = StubAlertService()
    worker = BehaviorWorker(
        settings=settings,
        queues=PipelineQueues(),
        event_bus=EventBus(),
        alert_service=alert_service,  # type: ignore[arg-type]
    )
    return worker, alert_service


def run_weapon_pass(
    worker: BehaviorWorker,
    alert_service: StubAlertService,
    detections: list[dict],
    zones: list[dict],
    now_start: float,
) -> None:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # First pass builds temporal state.
    worker._handle_weapon_detections(
        weapon_dets=detections,
        now=now_start,
        frame=frame,
        behavior_events=[],
        user_zones=zones,
        frame_w=640,
        frame_h=480,
        use_legacy=False,
    )

    # Second pass reaches consecutive threshold and should trigger alert.
    worker._handle_weapon_detections(
        weapon_dets=detections,
        now=now_start + 1.0,
        frame=frame,
        behavior_events=[],
        user_zones=zones,
        frame_w=640,
        frame_h=480,
        use_legacy=False,
    )

    assert alert_service.calls, "Expected a weapon alert to be created"


def test_weapon_outside_zone_creates_weapon_detected() -> None:
    worker, alert_service = make_worker()
    zones = [{"id": 1, "name": "Restricted", "x": 0.0, "y": 0.0, "width": 0.2, "height": 0.2}]
    detections = [{"class_name": "knife", "confidence": 0.91, "bbox": [500, 360, 620, 470]}]

    run_weapon_pass(worker, alert_service, detections, zones, now_start=100.0)

    alert = alert_service.calls[-1]
    metadata = alert.get("metadata", {})
    assert alert["event_type"] == "weapon_detected"
    assert metadata.get("event_type") == "weapon_detected"
    assert metadata.get("zone_id") is None


def test_weapon_inside_zone_creates_weapon_in_zone() -> None:
    worker, alert_service = make_worker()
    zones = [{"id": 7, "name": "Vault", "x": 0.2, "y": 0.2, "width": 0.25, "height": 0.25}]
    # Normalized bbox format to verify normalization compatibility path.
    detections = [{"class_name": "knife", "confidence": 0.95, "bbox": [0.24, 0.24, 0.35, 0.35]}]

    run_weapon_pass(worker, alert_service, detections, zones, now_start=200.0)

    alert = alert_service.calls[-1]
    metadata = alert.get("metadata", {})
    assert alert["event_type"] == "weapon_in_zone"
    assert alert.get("zone") == "Vault"
    assert metadata.get("event_type") == "weapon_in_zone"
    assert metadata.get("zone_id") == "7"


def test_multiple_zones_associates_correct_zone() -> None:
    worker, alert_service = make_worker()
    zones = [
        {"id": 1, "name": "Outer", "x": 0.0, "y": 0.0, "width": 0.12, "height": 0.12},
        {"id": 2, "name": "Armory", "x": 0.4, "y": 0.4, "width": 0.2, "height": 0.2},
    ]
    detections = [{"class_name": "knife", "confidence": 0.88, "bbox": [280, 220, 360, 300]}]

    run_weapon_pass(worker, alert_service, detections, zones, now_start=300.0)

    alert = alert_service.calls[-1]
    metadata = alert.get("metadata", {})
    assert alert["event_type"] == "weapon_in_zone"
    assert alert.get("zone") == "Armory"
    assert metadata.get("zone_id") == "2"


def test_no_false_positive_without_weapon_detection() -> None:
    worker, alert_service = make_worker()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    fired = worker._handle_weapon_detections(
        weapon_dets=[],
        now=400.0,
        frame=frame,
        behavior_events=[],
        user_zones=[{"id": 1, "name": "Zone", "x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5}],
        frame_w=640,
        frame_h=480,
        use_legacy=False,
    )

    assert fired is False
    assert alert_service.calls == []
