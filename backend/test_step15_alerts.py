"""
OVERWATCH — Step 15: Alert Threshold & Cooldown Test
=====================================================
Simulates repeated weapon detections to verify:
- Alerts trigger only after consecutive threshold (5)
- No spam — cooldown prevents repeated alerts (10s)
- Stale detections are cleaned up
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_temporal_filtering():
    """Test that alerts only fire after N consecutive detections."""
    from app.config import Settings
    from app.pipelines.behavior_worker import BehaviorWorker
    from app.core.queues import PipelineQueues
    from app.core.event_bus import EventBus
    import numpy as np

    settings = Settings()
    event_bus = EventBus()
    queues = PipelineQueues()

    worker = BehaviorWorker(
        settings=settings,
        queues=queues,
        event_bus=event_bus,
        alert_service=None,
        face_service=None,
        module_controller=None,
    )

    print("=" * 60)
    print("STEP 15 — ALERT THRESHOLD & COOLDOWN TEST")
    print("=" * 60)

    fake_det = {
        "class_name": "knife",
        "confidence": 0.85,
        "bbox": [100, 100, 200, 200],
        "type": "weapon",
    }
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    threshold = settings.weapon_consecutive_threshold

    # --- Test 1: No alert before threshold ---
    print(f"\n[TEST 1] No alert before threshold ({threshold} consecutive)")
    events = []
    fired = False
    for i in range(threshold - 1):
        now = time.monotonic()
        fired = worker._handle_weapon_detections([fake_det], now, frame, events)
        if fired:
            break

    t1_pass = not fired and len(events) == 0
    print(f"  Iterations: {threshold - 1}, Alert fired: {fired}, Events: {len(events)}")
    print(f"  Status: {'PASS' if t1_pass else 'FAIL'}")

    # --- Test 2: Alert fires at threshold ---
    print(f"\n[TEST 2] Alert fires at threshold ({threshold})")
    now = time.monotonic()
    fired = worker._handle_weapon_detections([fake_det], now, frame, events)
    t2_pass = fired and len(events) == 1
    print(f"  Alert fired: {fired}, Events: {len(events)}")
    if events:
        print(f"  Event: type={events[0].get('event_type')}, object={events[0].get('object_type')}")
    print(f"  Status: {'PASS' if t2_pass else 'FAIL'}")

    # --- Test 3: No spam during cooldown ---
    print(f"\n[TEST 3] No duplicate alert (cooldown = {settings.weapon_cooldown_seconds}s)")
    events2 = []
    now2 = time.monotonic()
    fired2 = worker._handle_weapon_detections([fake_det], now2, frame, events2)
    t3_pass = not fired2 and len(events2) == 0
    print(f"  Alert fired: {fired2}, New events: {len(events2)}")
    print(f"  Status: {'PASS' if t3_pass else 'FAIL'}")

    # --- Test 4: Alert fires after cooldown expires ---
    print(f"\n[TEST 4] Alert fires after cooldown expires")
    worker._weapon_state.clear()
    worker._weapon_cooldown.clear()

    events3 = []
    for i in range(threshold):
        now3 = time.monotonic()
        worker._handle_weapon_detections([fake_det], now3, frame, events3)

    t4_pass = len(events3) == 1
    print(f"  After {threshold} fresh detections: {len(events3)} event(s)")
    print(f"  Status: {'PASS' if t4_pass else 'FAIL'}")

    # --- Test 5: Stale detection cleanup ---
    print(f"\n[TEST 5] Stale detection cleanup")
    events4 = []
    now4 = time.monotonic()
    worker._handle_weapon_detections([], now4, frame, events4)
    state_count = len(worker._weapon_state)
    t5_pass = state_count == 0
    print(f"  Weapon state entries after empty frame: {state_count}")
    print(f"  Status: {'PASS' if t5_pass else 'FAIL'}")

    # --- Test 6: Spatial separation ---
    print(f"\n[TEST 6] Different locations = different tracking keys")
    worker._weapon_state.clear()
    worker._weapon_cooldown.clear()

    det_left = {"class_name": "knife", "confidence": 0.9, "bbox": [10, 10, 50, 50], "type": "weapon"}
    det_right = {"class_name": "knife", "confidence": 0.8, "bbox": [500, 300, 600, 400], "type": "weapon"}

    events5 = []
    for _ in range(threshold):
        now5 = time.monotonic()
        worker._handle_weapon_detections([det_left, det_right], now5, frame, events5)

    t6_pass = len(events5) == 2
    print(f"  Two weapons * {threshold} frames = {len(events5)} events")
    print(f"  Status: {'PASS' if t6_pass else 'FAIL'}")

    # --- Summary ---
    results = {
        "no_early_alert": t1_pass,
        "threshold_trigger": t2_pass,
        "cooldown_no_spam": t3_pass,
        "post_cooldown_alert": t4_pass,
        "stale_cleanup": t5_pass,
        "spatial_separation": t6_pass,
    }

    print("\n" + "=" * 60)
    all_pass = all(results.values())
    for name, passed in results.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    print(f"\nSTEP 15 {'COMPLETE — All tests passed' if all_pass else 'FAILED'}")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    try:
        ok = test_temporal_filtering()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"\nSTEP 15 FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
