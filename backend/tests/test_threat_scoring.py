from app.config import Settings
from app.core.event_bus import EventBus
from app.core.queues import PipelineQueues
from app.pipelines.behavior_worker import BehaviorWorker


def make_worker() -> BehaviorWorker:
    settings = Settings()
    return BehaviorWorker(
        settings=settings,
        queues=PipelineQueues(),
        event_bus=EventBus(),
        alert_service=None,
    )


def test_weapon_only_is_medium() -> None:
    worker = make_worker()
    signals = {
        "weapon_detected": True,
        "weapon_in_zone": False,
        "intrusion": False,
        "loitering": False,
        "crowd": False,
    }

    score = worker._compute_threat(signals)
    level = worker._get_threat_level(score)

    assert score >= worker._settings.threat_level_medium_threshold
    assert score < worker._settings.threat_level_high_threshold
    assert level == "MEDIUM"


def test_weapon_in_zone_is_high_or_critical() -> None:
    worker = make_worker()
    signals = {
        "weapon_detected": True,
        "weapon_in_zone": True,
        "intrusion": False,
        "loitering": False,
        "crowd": False,
    }

    score = worker._compute_threat(signals)
    level = worker._get_threat_level(score)

    assert score >= worker._settings.threat_level_high_threshold
    assert level in {"HIGH", "CRITICAL"}


def test_crowd_plus_weapon_is_high() -> None:
    worker = make_worker()
    signals = {
        "weapon_detected": True,
        "weapon_in_zone": False,
        "intrusion": False,
        "loitering": False,
        "crowd": True,
    }

    score = worker._compute_threat(signals)
    level = worker._get_threat_level(score)

    assert score >= worker._settings.threat_level_high_threshold
    assert level == "HIGH"


def test_no_events_is_low() -> None:
    worker = make_worker()
    signals = {
        "weapon_detected": False,
        "weapon_in_zone": False,
        "intrusion": False,
        "loitering": False,
        "crowd": False,
    }

    score = worker._compute_threat(signals)
    level = worker._get_threat_level(score)

    assert score == 0
    assert level == "LOW"
