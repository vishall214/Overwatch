"""
OVERWATCH — Zone Editor Testing Script
========================================
Comprehensive end-to-end testing for the Zone Editor feature.
Tests both backend (database, cache, pipeline) and validates API responses.
"""

import sys
import json
import time
import subprocess
import requests
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# ===== TEST CONFIGURATION =====
BASE_URL = "http://localhost:8000"
API_ZONES = f"{BASE_URL}/zones"
API_HEALTH = f"{BASE_URL}/health"

# Test results tracking
TESTS_PASSED = 0
TESTS_FAILED = 0
BUGS_FOUND = []

def log_pass(test_name: str, details: str = ""):
    """Log a passing test."""
    global TESTS_PASSED
    TESTS_PASSED += 1
    status = "✓ PASS" if not details else f"✓ PASS — {details}"
    print(f"  {status}: {test_name}")

def log_fail(test_name: str, details: str = "", bug: str = ""):
    """Log a failing test and optionally record a bug."""
    global TESTS_FAILED, BUGS_FOUND
    TESTS_FAILED += 1
    print(f"  ✗ FAIL: {test_name}")
    if details:
        print(f"    → {details}")
    if bug:
        BUGS_FOUND.append({"test": test_name, "bug": bug})
        print(f"    [BUG RECORDED]: {bug}")

def section(title: str):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def subsection(title: str):
    """Print a subsection header."""
    print(f"\n{title}")
    print("-" * 70)

def check_server_ready(max_retries: int = 20) -> bool:
    """Poll the server until it's ready or timeout."""
    print("\nWaiting for backend server to start...")
    for i in range(max_retries):
        try:
            resp = requests.get(API_HEALTH, timeout=2)
            if resp.status_code == 200:
                print(f"✓ Server is ready (attempt {i+1}/{max_retries})")
                return True
        except requests.exceptions.RequestException:
            if i < max_retries - 1:
                print(f"  Retry {i+1}/{max_retries}...")
                time.sleep(1)
    return False

# ===== BACKEND TESTING =====

def test_api_zone_create():
    """Test STEP 1 — Create Zone API endpoint."""
    subsection("STEP 1 — API Validation: Create Zone")
    
    payload = {
        "type": "intrusion",
        "x": 0.2,
        "y": 0.2,
        "width": 0.3,
        "height": 0.3,
        "name": "Test Intrusion Zone"
    }
    
    try:
        resp = requests.post(API_ZONES, json=payload, timeout=5)
        if resp.status_code == 201:
            data = resp.json()
            if all(k in data for k in ["id", "type", "x", "y", "width", "height"]):
                zone_id = data["id"]
                log_pass("POST /zones succeeded", f"Zone ID: {zone_id}")
                
                # Verify values match input
                if (data["type"] == payload["type"] and 
                    data["x"] == payload["x"] and 
                    data["y"] == payload["y"] and 
                    data["width"] == payload["width"] and 
                    data["height"] == payload["height"]):
                    log_pass("Zone values match input", "All coordinates and type correct")
                    return zone_id
                else:
                    log_fail("Zone values don't match input", f"Expected {payload}, got {data}")
                    return None
            else:
                log_fail("Response missing required fields", f"Got: {list(data.keys())}")
                return None
        else:
            log_fail(f"Unexpected status code: {resp.status_code}", resp.text)
            return None
    except requests.exceptions.RequestException as e:
        log_fail("Network error", str(e))
        return None

def test_api_zone_list():
    """Test STEP 1 — List Zones API endpoint."""
    subsection("STEP 1 — API Validation: List Zones")
    
    try:
        resp = requests.get(API_ZONES, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "zones" in data and "total" in data:
                total = data["total"]
                log_pass(f"GET /zones succeeded", f"Retrieved {total} zones")
                return data["zones"]
            else:
                log_fail("Response format invalid", f"Missing 'zones' or 'total' keys")
                return []
        else:
            log_fail(f"Unexpected status code: {resp.status_code}", resp.text)
            return []
    except requests.exceptions.RequestException as e:
        log_fail("Network error", str(e))
        return []

def test_api_zone_delete(zone_id: int):
    """Test STEP 1 — Delete Zone API endpoint."""
    subsection("STEP 1 — API Validation: Delete Zone")
    
    try:
        resp = requests.delete(f"{API_ZONES}/{zone_id}", timeout=5)
        if resp.status_code == 200:
            log_pass(f"DELETE /zones/{zone_id} succeeded")
            
            # Verify zone is gone
            resp_get = requests.get(API_ZONES, timeout=5)
            zones = resp_get.json().get("zones", [])
            if not any(z["id"] == zone_id for z in zones):
                log_pass("Zone successfully removed", "Not found in GET /zones")
                return True
            else:
                log_fail("Zone still exists after delete", "Found in GET /zones")
                bug = "DELETE endpoint doesn't properly remove zone from database or cache"
                BUGS_FOUND.append({"test": "API Delete", "bug": bug})
                return False
        else:
            log_fail(f"Unexpected status code: {resp.status_code}", resp.text)
            return False
    except requests.exceptions.RequestException as e:
        log_fail("Network error", str(e))
        return False

def test_database_structure():
    """Test STEP 2 — Verify database structure."""
    subsection("STEP 2 — Database Verification")
    
    try:
        from app.database.database import engine, SessionLocal
        from app.database.models import Zone
        from sqlalchemy import inspect
        
        # Check if zones table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "zones" in tables:
            log_pass("Zones table exists")
            
            # Check columns
            columns = inspector.get_columns("zones")
            col_names = {col["name"] for col in columns}
            required = {"id", "type", "x", "y", "width", "height", "is_active", "created_at"}
            
            if required.issubset(col_names):
                log_pass("All required columns present", f"Columns: {col_names}")
            else:
                missing = required - col_names
                log_fail("Missing columns", f"Missing: {missing}")
        else:
            log_fail("Zones table does not exist", f"Found tables: {tables}")
    except Exception as e:
        log_fail("Error inspecting database", str(e))

def test_cache_validation():
    """Test STEP 3 — Verify ZoneService cache behavior."""
    subsection("STEP 3 — Cache Validation")
    
    try:
        from app.services.zone_service import ZoneService
        from app.database.crud import create_zone
        from app.database.database import SessionLocal
        
        service = ZoneService()
        
        # Load zones into cache
        service.load_zones()
        cached = service.get_zones()
        
        if isinstance(cached, list):
            log_pass("ZoneService.load_zones() works", f"Loaded {len(cached)} zones")
            
            # Create a zone directly
            db = SessionLocal()
            try:
                zone = create_zone(
                    db,
                    zone_type="loitering",
                    x=0.1,
                    y=0.1,
                    width=0.2,
                    height=0.2,
                    name="Cache Test Zone"
                )
                db_zone_id = zone.id
                
                # Verify cache is stale (old data)
                stale_cached = service.get_zones()
                if not any(z["id"] == db_zone_id for z in stale_cached):
                    log_pass("Cache correctly doesn't auto-refresh", "Cache is read-only during operations")
                
                # Reload cache
                service.reload()
                refreshed = service.get_zones()
                if any(z["id"] == db_zone_id for z in refreshed):
                    log_pass("Cache reloads correctly after reload()", "New zone found after reload")
                else:
                    log_fail("Cache reload failed", "New zone not found in cache after reload()")
                
                # Clean up
                from app.database.crud import delete_zone
                delete_zone(db, db_zone_id)
            finally:
                db.close()
        else:
            log_fail("ZoneService.get_zones() return type invalid", f"Got: {type(cached)}")
    except Exception as e:
        log_fail("Error testing cache", str(e))

def test_zone_coordinates():
    """Test STEP 2 — Verify zone coordinates are normalized (0-1)."""
    subsection("STEP 2 — Database Verification: Coordinates")
    
    try:
        resp = requests.post(API_ZONES, json={
            "type": "crowd",
            "x": 0.0,
            "y": 0.0,
            "width": 1.0,
            "height": 1.0,
            "name": "Full Frame"
        }, timeout=5)
        
        if resp.status_code == 201:
            data = resp.json()
            if (0 <= data["x"] <= 1 and 0 <= data["y"] <= 1 and 
                0 <= data["width"] <= 1 and 0 <= data["height"] <= 1):
                log_pass("Coordinates are normalized (0-1 range)")
                
                # Clean up
                requests.delete(f"{API_ZONES}/{data['id']}", timeout=5)
            else:
                log_fail("Coordinates outside 0-1 range", f"x={data['x']}, y={data['y']}, w={data['width']}, h={data['height']}")
        else:
            log_fail(f"Failed to create zone: {resp.status_code}")
    except Exception as e:
        log_fail("Error testing coordinates", str(e))

def test_multiple_zones():
    """Test STEP 5 — Multiple zones with different types."""
    subsection("STEP 5 — Multiple Zones Test")
    
    zone_ids = []
    
    try:
        # Create intrusion zone
        resp1 = requests.post(API_ZONES, json={
            "type": "intrusion",
            "x": 0.1,
            "y": 0.1,
            "width": 0.2,
            "height": 0.2
        }, timeout=5)
        if resp1.status_code == 201:
            zone_ids.append(resp1.json()["id"])
            log_pass("Intrusion zone created")
        
        # Create loitering zone
        resp2 = requests.post(API_ZONES, json={
            "type": "loitering",
            "x": 0.5,
            "y": 0.5,
            "width": 0.25,
            "height": 0.25
        }, timeout=5)
        if resp2.status_code == 201:
            zone_ids.append(resp2.json()["id"])
            log_pass("Loitering zone created")
        
        # Create crowd zone
        resp3 = requests.post(API_ZONES, json={
            "type": "crowd",
            "x": 0.7,
            "y": 0.7,
            "width": 0.25,
            "height": 0.25
        }, timeout=5)
        if resp3.status_code == 201:
            zone_ids.append(resp3.json()["id"])
            log_pass("Crowd zone created")
        
        # Verify all are in list
        resp_list = requests.get(API_ZONES, timeout=5)
        zones = resp_list.json()["zones"]
        for zid in zone_ids:
            if any(z["id"] == zid for z in zones):
                continue
            else:
                log_fail(f"Zone {zid} not found in list")
        
        if len(zone_ids) == 3:
            log_pass(f"All {len(zone_ids)} zones created and retrievable")
        
        # Clean up
        for zid in zone_ids:
            requests.delete(f"{API_ZONES}/{zid}", timeout=5)
        
    except Exception as e:
        log_fail("Error testing multiple zones", str(e))

def test_edge_cases():
    """Test STEP 6 — Edge cases."""
    subsection("STEP 6 — Edge Cases")
    
    try:
        # Very small zone
        resp_small = requests.post(API_ZONES, json={
            "type": "intrusion",
            "x": 0.5,
            "y": 0.5,
            "width": 0.01,
            "height": 0.01
        }, timeout=5)
        if resp_small.status_code == 201:
            log_pass("Very small zone created")
            small_id = resp_small.json()["id"]
            requests.delete(f"{API_ZONES}/{small_id}", timeout=5)
        
        # Zone at boundary (0, 0)
        resp_corner1 = requests.post(API_ZONES, json={
            "type": "intrusion",
            "x": 0.0,
            "y": 0.0,
            "width": 0.1,
            "height": 0.1
        }, timeout=5)
        if resp_corner1.status_code == 201:
            log_pass("Zone at (0, 0) boundary created")
            id1 = resp_corner1.json()["id"]
            requests.delete(f"{API_ZONES}/{id1}", timeout=5)
        
        # Zone at boundary (1, 1)
        resp_corner2 = requests.post(API_ZONES, json={
            "type": "intrusion",
            "x": 0.9,
            "y": 0.9,
            "width": 0.1,
            "height": 0.1
        }, timeout=5)
        if resp_corner2.status_code == 201:
            log_pass("Zone at (1, 1) boundary created")
            id2 = resp_corner2.json()["id"]
            requests.delete(f"{API_ZONES}/{id2}", timeout=5)
        
        # Overlapping zones
        resp_z1 = requests.post(API_ZONES, json={
            "type": "intrusion",
            "x": 0.2,
            "y": 0.2,
            "width": 0.3,
            "height": 0.3
        }, timeout=5)
        resp_z2 = requests.post(API_ZONES, json={
            "type": "loitering",
            "x": 0.35,
            "y": 0.35,
            "width": 0.3,
            "height": 0.3
        }, timeout=5)
        if resp_z1.status_code == 201 and resp_z2.status_code == 201:
            log_pass("Overlapping zones created without error")
            requests.delete(f"{API_ZONES}/{resp_z1.json()['id']}", timeout=5)
            requests.delete(f"{API_ZONES}/{resp_z2.json()['id']}", timeout=5)
    
    except Exception as e:
        log_fail("Error testing edge cases", str(e))

# ===== MAIN TEST RUNNER =====

def main():
    """Run all tests."""
    
    print("\n" + "="*70)
    print("  OVERWATCH — ZONE EDITOR FEATURE TESTING")
    print("  Comprehensive End-to-End Validation")
    print("="*70)
    
    section("PHASE 1: STARTUP & CONNECTIVITY")
    
    # Check if server is running
    try:
        resp = requests.get(API_HEALTH, timeout=2)
        if resp.status_code == 200:
            print("✓ Backend server is already running")
    except:
        print("Backend server not detected. You may need to start it manually:")
        print("  cd backend")
        print("  uvicorn app.main:app --reload --port 8000")
        print("\nAttempting to continue with tests that don't require the server...")
    
    if not check_server_ready():
        print("\n⚠ Server not ready. Some tests will be skipped.\n")
    
    # Database tests (don't need server)
    section("PHASE 2: DATABASE & INITIALIZATION TESTS")
    test_database_structure()
    test_cache_validation()
    
    # API tests (need server)
    section("PHASE 3: API ENDPOINT TESTING")
    try:
        # STEP 1: API Validation
        zone_id = test_api_zone_create()
        zones = test_api_zone_list()
        if zone_id:
            test_api_zone_delete(zone_id)
        
        # STEP 2: Database & coordinates
        test_zone_coordinates()
        
        # STEP 5: Multiple zones
        test_multiple_zones()
        
        # STEP 6: Edge cases
        test_edge_cases()
        
    except Exception as e:
        print(f"\n✗ API testing failed: {e}")
    
    # Summary
    section("TEST SUMMARY")
    print(f"\n✓ Tests Passed: {TESTS_PASSED}")
    print(f"✗ Tests Failed: {TESTS_FAILED}")
    print(f"Total: {TESTS_PASSED + TESTS_FAILED}")
    
    if BUGS_FOUND:
        print(f"\n⚠ BUGS FOUND ({len(BUGS_FOUND)}):")
        for i, bug in enumerate(BUGS_FOUND, 1):
            print(f"  {i}. [{bug['test']}] {bug['bug']}")
    else:
        print(f"\n✓ No bugs found!")
    
    success_rate = (TESTS_PASSED / (TESTS_PASSED + TESTS_FAILED) * 100) if (TESTS_PASSED + TESTS_FAILED) > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    print("\n" + "="*70)
    print("  End of Test Report")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
