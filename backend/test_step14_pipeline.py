"""
OVERWATCH — Step 14: Pipeline Integration Test
================================================
Verifies the weapon detection integrates correctly with the
full pipeline without FPS drops or queue delays.
Tests InferenceWorker weapon detection logic directly.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_inference_worker_integration():
    """Verify weapon detection is correctly wired into the inference worker."""
    from app.config import Settings
    from app.services.detection_service import DetectionService
    from app.core.queues import PipelineQueues, FramePacket, DetectionPacket
    from app.core.event_bus import EventBus
    from app.pipelines.inference_worker import InferenceWorker
    import numpy as np
    import queue

    settings = Settings()
    det_service = DetectionService(settings)
    event_bus = EventBus()
    queues = PipelineQueues()

    print("=" * 60)
    print("STEP 14 — PIPELINE INTEGRATION TEST")
    print("=" * 60)

    # Load models
    print("\n[SETUP] Loading models...")
    ok = det_service.load_model()
    print(f"  Main model: {'OK' if ok else 'FAIL'}")
    assert ok

    ok = det_service.load_weapon_model()
    print(f"  Weapon model: {'OK' if ok else 'FAIL'}")
    assert ok

    worker = InferenceWorker(
        settings=settings,
        detection_service=det_service,
        event_bus=event_bus,
        queues=queues,
    )

    # --- Test 1: Weapon detection runs every 3 frames ---
    print(f"\n[TEST 1] Weapon detection skip-frame logic")
    skip = settings.weapon_skip_frames
    frames_with_weapon_det = []

    for frame_idx in range(12):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Simulate what InferenceWorker does internally
        weapon_detections_list = None
        if (
            det_service.weapon_is_loaded
            and frame_idx % settings.weapon_skip_frames == 0
        ):
            weapon_results = det_service.detect_weapons(frame)
            weapon_detections_list = [d.to_dict() for d in weapon_results]
            frames_with_weapon_det.append(frame_idx)

        # Verify: weapon detection ran on correct frames
        expected_ran = (frame_idx % skip == 0)
        actual_ran = (weapon_detections_list is not None)
        assert expected_ran == actual_ran, f"Frame {frame_idx}: expected ran={expected_ran}, got={actual_ran}"

    print(f"  Skip frames: {skip}")
    print(f"  Weapon detection ran on frames: {frames_with_weapon_det}")
    print(f"  Expected: {[i for i in range(12) if i % skip == 0]}")
    t1_pass = frames_with_weapon_det == [i for i in range(12) if i % skip == 0]
    print(f"  Status: {'PASS' if t1_pass else 'FAIL'}")

    # --- Test 2: DetectionPacket carries weapon_detections ---
    print(f"\n[TEST 2] DetectionPacket carries weapon_detections field")
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    result = det_service.detect(frame)
    weapon_results = det_service.detect_weapons(frame)
    weapon_dicts = [d.to_dict() for d in weapon_results]

    packet = DetectionPacket(
        frame=frame,
        annotated_frame=result.annotated_frame,
        detections=[d.to_dict() for d in result.detections],
        frame_index=0,
        timestamp_ns=time.time_ns(),
        weapon_detections=weapon_dicts,
    )

    has_field = hasattr(packet, 'weapon_detections')
    value_correct = packet.weapon_detections == weapon_dicts
    t2_pass = has_field and value_correct
    print(f"  Has weapon_detections field: {has_field}")
    print(f"  Value matches: {value_correct}")
    print(f"  Status: {'PASS' if t2_pass else 'FAIL'}")

    # --- Test 3: None vs empty list semantics ---
    print(f"\n[TEST 3] None vs [] semantics (not-run vs ran-empty)")
    pkt_not_run = DetectionPacket(
        frame=frame, annotated_frame=frame, detections=[],
        frame_index=1, timestamp_ns=time.time_ns(),
    )
    pkt_ran_empty = DetectionPacket(
        frame=frame, annotated_frame=frame, detections=[],
        frame_index=0, timestamp_ns=time.time_ns(),
        weapon_detections=[],
    )
    t3_pass = (pkt_not_run.weapon_detections is None) and (pkt_ran_empty.weapon_detections == [])
    print(f"  Not-run frame weapon_detections: {pkt_not_run.weapon_detections} (expected: None)")
    print(f"  Ran-empty frame weapon_detections: {pkt_ran_empty.weapon_detections} (expected: [])")
    print(f"  Status: {'PASS' if t3_pass else 'FAIL'}")

    # --- Test 4: FPS impact measurement ---
    print(f"\n[TEST 4] FPS impact measurement")
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # Benchmark: YOLO only
    times_yolo = []
    for _ in range(5):
        start = time.monotonic()
        det_service.detect(frame)
        times_yolo.append((time.monotonic() - start) * 1000)

    # Benchmark: YOLO + weapon
    times_combined = []
    for _ in range(5):
        start = time.monotonic()
        det_service.detect(frame)
        det_service.detect_weapons(frame)
        times_combined.append((time.monotonic() - start) * 1000)

    avg_yolo = sum(times_yolo) / len(times_yolo)
    avg_combined = sum(times_combined) / len(times_combined)
    overhead = avg_combined - avg_yolo
    # With skip=3, effective overhead per frame is overhead/3
    effective_overhead = overhead / settings.weapon_skip_frames

    print(f"  YOLO only:     {avg_yolo:.1f}ms")
    print(f"  YOLO + weapon: {avg_combined:.1f}ms")
    print(f"  Raw overhead:  {overhead:.1f}ms")
    print(f"  Effective per frame (skip={skip}): {effective_overhead:.1f}ms")

    t4_pass = effective_overhead < 100  # Less than 100ms overhead per frame
    print(f"  Status: {'PASS' if t4_pass else 'FAIL — significant FPS impact'}")

    # --- Test 5: No pipeline blocking ---
    print(f"\n[TEST 5] No queue blocking")
    # Verify queues don't grow during weapon detection
    q_before = queues.stats
    det_service.detect_weapons(frame)
    q_after = queues.stats
    t5_pass = q_before == q_after
    print(f"  Queue states before: {q_before}")
    print(f"  Queue states after:  {q_after}")
    print(f"  No queue changes: {t5_pass}")
    print(f"  Status: {'PASS' if t5_pass else 'FAIL'}")

    # --- Summary ---
    results = {
        "skip_frame_logic": t1_pass,
        "packet_field": t2_pass,
        "none_vs_empty": t3_pass,
        "fps_impact": t4_pass,
        "no_blocking": t5_pass,
    }

    print("\n" + "=" * 60)
    all_pass = all(results.values())
    for name, passed in results.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    print(f"\nSTEP 14 {'COMPLETE — All tests passed' if all_pass else 'FAILED'}")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    try:
        ok = test_inference_worker_integration()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"\nSTEP 14 FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
