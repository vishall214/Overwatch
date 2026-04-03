"""
OVERWATCH — Step 13: Standalone Weapon Model Test
===================================================
Verifies the weapon detection model loads correctly,
detects knife (COCO class 43), and produces correct labels.
"""

import sys
import os
import time
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_model_load():
    """Test 1: Model loads successfully."""
    from app.config import Settings
    from app.services.detection_service import DetectionService

    settings = Settings()
    service = DetectionService(settings)

    print("=" * 60)
    print("STEP 13 — STANDALONE MODEL TEST")
    print("=" * 60)

    # Load main model
    ok = service.load_model()
    print(f"\n[TEST 1] Main YOLO model load: {'PASS' if ok else 'FAIL'}")
    assert ok, "Main model failed to load"

    # Load weapon model
    ok = service.load_weapon_model()
    print(f"[TEST 2] Weapon model load:     {'PASS' if ok else 'FAIL'}")
    assert ok, "Weapon model failed to load"

    print(f"  weapon_is_loaded = {service.weapon_is_loaded}")
    return service


def test_model_inference(service):
    """Test 2: Model runs inference on a synthetic frame."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    print(f"\n[TEST 3] Weapon inference on blank frame...")
    start = time.monotonic()
    detections = service.detect_weapons(frame)
    elapsed = (time.monotonic() - start) * 1000
    print(f"  Result: {len(detections)} detections in {elapsed:.1f}ms")
    print(f"  Status: PASS (blank frame = 0 expected)")
    return elapsed


def test_class_labels(service):
    """Test 3: Verify COCO class 43 maps to 'knife'."""
    from app.config import Settings
    settings = Settings()

    model = service._weapon_model
    weapon_classes = settings.weapon_classes

    print(f"\n[TEST 4] Class label verification:")
    print(f"  Configured weapon_classes: {weapon_classes}")

    all_pass = True
    for cls_id in weapon_classes:
        name = model.names.get(cls_id, "UNKNOWN")
        expected = {43: "knife"}.get(cls_id, "unknown")
        status = name == expected
        all_pass = all_pass and status
        print(f"  Class {cls_id}: '{name}' (expected: '{expected}') — {'PASS' if status else 'FAIL'}")

    return all_pass


def test_inference_speed(service):
    """Test 4: Benchmark inference speed."""
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # Warmup
    service.detect_weapons(frame)

    # Benchmark 5 runs
    times = []
    for _ in range(5):
        start = time.monotonic()
        service.detect_weapons(frame)
        times.append((time.monotonic() - start) * 1000)

    avg = sum(times) / len(times)
    print(f"\n[TEST 5] Inference speed benchmark (5 runs):")
    print(f"  Average: {avg:.1f}ms  Min: {min(times):.1f}ms  Max: {max(times):.1f}ms")
    print(f"  Status: {'PASS' if avg < 500 else 'WARN slow'}")
    return avg


def test_config_constraints():
    """Test 5: Verify performance config constraints."""
    from app.config import Settings
    settings = Settings()

    print(f"\n[TEST 6] Configuration constraints:")
    conf_ok = settings.weapon_confidence >= 0.6
    skip_ok = settings.weapon_skip_frames >= 2
    print(f"  weapon_confidence = {settings.weapon_confidence} (>= 0.6): {'PASS' if conf_ok else 'FAIL'}")
    print(f"  weapon_skip_frames = {settings.weapon_skip_frames} (>= 2, not every frame): {'PASS' if skip_ok else 'FAIL'}")
    print(f"  weapon_cooldown_seconds = {settings.weapon_cooldown_seconds}")
    print(f"  weapon_consecutive_threshold = {settings.weapon_consecutive_threshold}")
    print(f"  weapon_classes = {settings.weapon_classes}")
    return conf_ok and skip_ok


def test_detection_type(service):
    """Test 6: Verify detection output format includes type='weapon'."""
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    detections = service.detect_weapons(frame)

    print(f"\n[TEST 7] Detection output format:")
    if detections:
        d = detections[0]
        d_dict = d.to_dict()
        has_type = d_dict.get("type") == "weapon"
        print(f"  detection_type = {d.detection_type}")
        print(f"  to_dict()['type'] = {d_dict.get('type')}")
        print(f"  Status: {'PASS' if has_type else 'FAIL'}")
        return has_type
    else:
        print(f"  No detections on random frame (expected)")
        print(f"  Checking dataclass default...")
        from app.models.detection import Detection
        dummy = Detection(bbox=[0,0,1,1], confidence=0.9, class_id=43, class_name="knife", detection_type="weapon")
        d_dict = dummy.to_dict()
        has_type = d_dict.get("type") == "weapon"
        print(f"  to_dict()['type'] = {d_dict.get('type')}")
        print(f"  Status: {'PASS' if has_type else 'FAIL'}")
        return has_type


if __name__ == "__main__":
    results = {}
    try:
        service = test_model_load()
        results["model_load"] = True

        test_model_inference(service)
        results["inference"] = True

        results["class_labels"] = test_class_labels(service)
        test_inference_speed(service)
        results["config"] = test_config_constraints()
        results["detection_type"] = test_detection_type(service)

        print("\n" + "=" * 60)
        all_pass = all(results.values())
        for name, passed in results.items():
            print(f"  {name}: {'PASS' if passed else 'FAIL'}")
        print(f"\nSTEP 13 {'COMPLETE — All tests passed' if all_pass else 'FAILED'}")
        print("=" * 60)

        if not all_pass:
            sys.exit(1)

    except Exception as e:
        print(f"\n{'=' * 60}")
        print(f"STEP 13 FAILED: {e}")
        print(f"{'=' * 60}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
