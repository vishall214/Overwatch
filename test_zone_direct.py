"""
OVERWATCH — Direct Zone Editor Database Testing
=================================================
Tests the zone editor without requiring the FastAPI server running.
Uses SQLAlchemy directly to test database operations and service logic.
"""

import sys
import os
from pathlib import Path

# Force SQLite fallback by temporarily renaming .env
# (PostgreSQL may not be running for CI/local testing)
import shutil
env_file = Path(__file__).parent / ".env"
env_backup = None
if env_file.exists():
    env_backup = Path(__file__).parent / ".env.backup"
    shutil.move(str(env_file), str(env_backup))

try:
    # Add backend to path
    backend_path = Path(__file__).parent / "backend"
    sys.path.insert(0, str(backend_path))

    # ===== IMPORTS =====
    from app.database.database import engine, SessionLocal, Base
finally:
    # Restore .env
    if env_backup and env_backup.exists():
        shutil.move(str(env_backup), str(env_file))
from app.database.models import Zone
from app.database.crud import create_zone, get_zones, delete_zone
from app.services.zone_service import ZoneService
from app.utils.geometry_utils import rect_intersects_bbox, bbox_center

# Test tracking
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

# ===== DATABASE SETUP =====

def setup_database():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created/verified")

def cleanup_all_zones():
    """Delete all zones from database."""
    db = SessionLocal()
    try:
        db.query(Zone).delete()
        db.commit()
    finally:
        db.close()

# ===== STEP 1: API VALIDATION (via direct DB calls) =====

def test_zone_creation():
    """Test STEP 1 — Zone creation in database."""
    subsection("STEP 1 — Zone Creation (Database)")
    
    db = SessionLocal()
    try:
        zone = create_zone(
            db,
            zone_type="intrusion",
            x=0.2,
            y=0.2,
            width=0.3,
            height=0.3,
            name="Test Intrusion Zone"
        )
        
        if zone.id and zone.type == "intrusion":
            log_pass("Zone created successfully", f"ID: {zone.id}")
            
            # Verify values
            if (zone.x == 0.2 and zone.y == 0.2 and 
                zone.width == 0.3 and zone.height == 0.3):
                log_pass("Zone coordinates preserved", "All values match input")
            else:
                log_fail("Zone coordinates corrupted", f"x={zone.x}, y={zone.y}, w={zone.width}, h={zone.height}")
            
            return zone.id
        else:
            log_fail("Zone creation failed", f"ID: {zone.id}, Type: {zone.type}")
            return None
    except Exception as e:
        log_fail("Exception during zone creation", str(e))
        return None
    finally:
        db.close()

def test_zone_retrieval(zone_id: int):
    """Test STEP 1 — Zone retrieval from database."""
    subsection("STEP 1 — Zone Retrieval (Database)")
    
    db = SessionLocal()
    try:
        zones = get_zones(db)
        
        if zones:
            log_pass(f"get_zones() returned {len(zones)} zone(s)")
            
            zone = next((z for z in zones if z.id == zone_id), None)
            if zone:
                log_pass(f"Created zone found in list", f"Zone ID: {zone_id}")
                return zone
            else:
                log_fail(f"Created zone not found", f"Looking for ID: {zone_id}")
                bug = "Zone not persisted or not retrieved correctly"
                BUGS_FOUND.append({"test": "Zone Retrieval", "bug": bug})
                return None
        else:
            log_fail("get_zones() returned empty list", "Expected at least one zone")
            return None
    except Exception as e:
        log_fail("Exception during zone retrieval", str(e))
        return None
    finally:
        db.close()

def test_zone_deletion(zone_id: int):
    """Test STEP 1 — Zone deletion from database."""
    subsection("STEP 1 — Zone Deletion (Database)")
    
    db = SessionLocal()
    try:
        deleted = delete_zone(db, zone_id)
        
        if deleted:
            log_pass(f"Zone {zone_id} deleted successfully")
            
            # Verify it's gone
            zones = get_zones(db)
            if not any(z.id == zone_id for z in zones):
                log_pass(f"Zone {zone_id} confirmed removed from database")
            else:
                log_fail(f"Zone {zone_id} still exists after deletion")
                bug = "delete_zone() doesn't properly persist deletion"
                BUGS_FOUND.append({"test": "Zone Deletion", "bug": bug})
        else:
            log_fail(f"delete_zone() returned False for zone {zone_id}")
    except Exception as e:
        log_fail("Exception during zone deletion", str(e))
    finally:
        db.close()

# ===== STEP 2: DATABASE VERIFICATION =====

def test_database_structure():
    """Test STEP 2 — Verify database schema."""
    subsection("STEP 2 — Database Structure Verification")
    
    try:
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "zones" in tables:
            log_pass("Zones table exists")
            
            columns = inspector.get_columns("zones")
            col_names = {col["name"] for col in columns}
            col_types = {col["name"]: str(col["type"]) for col in columns}
            
            required_cols = {"id", "type", "x", "y", "width", "height", "is_active", "created_at"}
            if required_cols.issubset(col_names):
                log_pass("All required columns present", f"Columns: {sorted(col_names)}")
            else:
                missing = required_cols - col_names
                log_fail("Missing required columns", f"Missing: {missing}")
            
            # Check column types
            expected_types = {
                "x": "FLOAT",
                "y": "FLOAT",
                "width": "FLOAT",
                "height": "FLOAT"
            }
            
            for col, expected_type in expected_types.items():
                if col in col_types:
                    if expected_type in col_types[col]:
                        continue
                    else:
                        log_fail(f"Column '{col}' has unexpected type", 
                                f"Expected FLOAT-like, got {col_types[col]}")
        else:
            log_fail("Zones table does not exist", f"Tables found: {tables}")
    except Exception as e:
        log_fail("Error inspecting database schema", str(e))

def test_coordinate_normalization():
    """Test STEP 2 — Verify coordinates are stored in 0-1 range."""
    subsection("STEP 2 — Coordinate Normalization Verification")
    
    db = SessionLocal()
    try:
        # Test boundary values
        test_zones = [
            ("boundary_00", 0.0, 0.0, 0.1, 0.1),
            ("boundary_11", 0.9, 0.9, 0.1, 0.1),
            ("small", 0.45, 0.45, 0.01, 0.01),
            ("large", 0.0, 0.0, 1.0, 1.0),
        ]
        
        zone_ids = []
        for name, x, y, w, h in test_zones:
            zone = create_zone(db, "intrusion", x, y, w, h, name)
            zone_ids.append(zone.id)
        
        zones = get_zones(db)
        for zone in zones:
            if zone.id in zone_ids:
                if (0 <= zone.x <= 1 and 0 <= zone.y <= 1 and 
                    0 <= zone.width <= 1 and 0 <= zone.height <= 1):
                    log_pass(f"Zone '{zone.name}' coordinates in 0-1 range")
                else:
                    log_fail(f"Zone '{zone.name}' coordinates out of range",
                            f"x={zone.x}, y={zone.y}, w={zone.width}, h={zone.height}")
        
        # Clean up
        for zid in zone_ids:
            delete_zone(db, zid)
    except Exception as e:
        log_fail("Error testing coordinate normalization", str(e))
    finally:
        db.close()

# ===== STEP 3: CACHE VALIDATION =====

def test_zone_service_loading():
    """Test STEP 3 — ZoneService loads zones into memory."""
    subsection("STEP 3 — Zone Service Loading")
    
    try:
        service = ZoneService()
        
        # Create a test zone
        db = SessionLocal()
        try:
            zone = create_zone(db, "loitering", 0.3, 0.3, 0.2, 0.2, "Service Test Zone")
            test_zone_id = zone.id
        finally:
            db.close()
        
        # Load zones
        service.load_zones()
        cached = service.get_zones()
        
        if isinstance(cached, list):
            log_pass("ZoneService.load_zones() successful", f"Loaded {len(cached)} zones")
            
            if any(z["id"] == test_zone_id for z in cached):
                log_pass("Created zone found in cache")
            else:
                log_fail("Created zone not in cache after load_zones()")
        else:
            log_fail("get_zones() didn't return a list", f"Got: {type(cached)}")
        
        # Clean up
        db = SessionLocal()
        try:
            delete_zone(db, test_zone_id)
        finally:
            db.close()
    except Exception as e:
        log_fail("Error testing zone service loading", str(e))

def test_zone_service_caching():
    """Test STEP 3 — ZoneService read-only during operations."""
    subsection("STEP 3 — Zone Service Cache Behavior")
    
    try:
        service = ZoneService()
        service.load_zones()
        
        initial_cache = service.get_zones()
        initial_count = len(initial_cache)
        
        # Create a zone (cache not reloaded yet)
        db = SessionLocal()
        try:
            zone = create_zone(db, "crowd", 0.4, 0.4, 0.2, 0.2, "Cache Test")
            test_zone_id = zone.id
        finally:
            db.close()
        
        # Check cache still has old count (not auto-refreshed)
        stale_cache = service.get_zones()
        if len(stale_cache) == initial_count:
            log_pass("Cache remains unchanged after DB write (no auto-refresh)", "Cache is read-only")
        else:
            log_fail("Cache auto-refreshed (unexpected)", 
                    f"Expected {initial_count}, got {len(stale_cache)}")
        
        # Reload
        service.reload()
        refreshed_cache = service.get_zones()
        
        if any(z["id"] == test_zone_id for z in refreshed_cache):
            log_pass("Cache reloaded successfully", "New zone found after reload()")
        else:
            log_fail("Zone not in cache after reload()", "reload() may not be working")
        
        # Clean up
        db = SessionLocal()
        try:
            delete_zone(db, test_zone_id)
        finally:
            db.close()
    except Exception as e:
        log_fail("Error testing cache behavior", str(e))

# ===== STEP 5: MULTIPLE ZONES =====

def test_multiple_zones_independent():
    """Test STEP 5 — Multiple zones behave independently."""
    subsection("STEP 5 — Multiple Zones Independence")
    
    db = SessionLocal()
    try:
        # Create different zone types
        intrusion_zone = create_zone(db, "intrusion", 0.1, 0.1, 0.2, 0.2, "Intrusion")
        loitering_zone = create_zone(db, "loitering", 0.5, 0.5, 0.25, 0.25, "Loitering")
        crowd_zone = create_zone(db, "crowd", 0.7, 0.7, 0.25, 0.25, "Crowd")
        
        zones = get_zones(db)
        intrusion = next((z for z in zones if z.type == "intrusion"), None)
        loitering = next((z for z in zones if z.type == "loitering"), None)
        crowd = next((z for z in zones if z.type == "crowd"), None)
        
        if all([intrusion, loitering, crowd]):
            log_pass("All three zone types created and retrievable")
            
            # Verify no cross-contamination
            if (intrusion.type == "intrusion" and loitering.type == "loitering" and 
                crowd.type == "crowd"):
                log_pass("Zone types are correct (no cross-contamination)")
            else:
                log_fail("Zone types corrupted", 
                        f"intrusion={intrusion.type}, loitering={loitering.type}, crowd={crowd.type}")
        else:
            log_fail("Not all zone types created", 
                    f"intrusion={intrusion}, loitering={loitering}, crowd={crowd}")
        
        # Clean up
        delete_zone(db, intrusion_zone.id)
        delete_zone(db, loitering_zone.id)
        delete_zone(db, crowd_zone.id)
    except Exception as e:
        log_fail("Error testing multiple zones", str(e))
    finally:
        db.close()

# ===== STEP 6: EDGE CASES =====

def test_edge_cases():
    """Test STEP 6 — Edge cases and boundary conditions."""
    subsection("STEP 6 — Edge Cases")
    
    db = SessionLocal()
    try:
        # Very small zone
        try:
            small_zone = create_zone(db, "intrusion", 0.5, 0.5, 0.001, 0.001, "Tiny")
            log_pass("Very small zone created")
            delete_zone(db, small_zone.id)
        except Exception as e:
            log_fail("Very small zone failed", str(e))
        
        # Zone at (0, 0)
        try:
            corner_zone = create_zone(db, "intrusion", 0.0, 0.0, 0.1, 0.1, "Corner 0,0")
            log_pass("Zone at (0, 0) boundary created")
            delete_zone(db, corner_zone.id)
        except Exception as e:
            log_fail("Corner (0, 0) zone failed", str(e))
        
        # Zone at (1, 1)
        try:
            corner_zone2 = create_zone(db, "intrusion", 0.9, 0.9, 0.1, 0.1, "Corner 1,1")
            log_pass("Zone at (1, 1) boundary created")
            delete_zone(db, corner_zone2.id)
        except Exception as e:
            log_fail("Corner (1, 1) zone failed", str(e))
        
        # Overlapping zones
        try:
            z1 = create_zone(db, "intrusion", 0.2, 0.2, 0.3, 0.3, "Overlap1")
            z2 = create_zone(db, "loitering", 0.35, 0.35, 0.3, 0.3, "Overlap2")
            log_pass("Overlapping zones created successfully")
            delete_zone(db, z1.id)
            delete_zone(db, z2.id)
        except Exception as e:
            log_fail("Overlapping zones failed", str(e))
        
        # Full-frame zone
        try:
            full = create_zone(db, "intrusion", 0.0, 0.0, 1.0, 1.0, "Full")
            log_pass("Full-frame zone (0,0,1,1) created")
            delete_zone(db, full.id)
        except Exception as e:
            log_fail("Full-frame zone failed", str(e))
    except Exception as e:
        log_fail("Unexpected error in edge case testing", str(e))
    finally:
        db.close()

# ===== GEOMETRY UTILITIES TESTING =====

def test_geometry_utilities():
    """Test STEP 4 — Geometry intersection utilities."""
    subsection("STEP 4 — Geometry Utilities")
    
    try:
        # Test rect_intersects_bbox
        zone = {
            "x": 0.2,
            "y": 0.2,
            "width": 0.3,
            "height": 0.3,
            "id": 1,
            "type": "intrusion"
        }
        
        # Test case 1: Object clearly inside zone
        bbox_inside = [320, 320, 400, 400]  # Inside 0.2-0.5, 0.2-0.5 area
        frame_w, frame_h = 1600, 1600
        
        intersects = rect_intersects_bbox(zone, bbox_inside, frame_w, frame_h)
        if intersects:
            log_pass("rect_intersects_bbox detects object inside zone")
        else:
            log_fail("rect_intersects_bbox missed object inside zone")
            bug = "Intersection detection logic may be broken"
            BUGS_FOUND.append({"test": "Geometry", "bug": bug})
        
        # Test case 2: Object clearly outside zone
        bbox_outside = [1000, 1000, 1100, 1100]  # Outside 0.2-0.5 area
        
        intersects = rect_intersects_bbox(zone, bbox_outside, frame_w, frame_h)
        if not intersects:
            log_pass("rect_intersects_bbox correctly rejects outside object")
        else:
            log_fail("rect_intersects_bbox false positive for outside object")
        
        # Test bbox_center
        center = bbox_center([100, 100, 300, 300])
        if center == (200, 200):
            log_pass("bbox_center calculates correctly")
        else:
            log_fail(f"bbox_center incorrect: expected (200, 200), got {center}")
    except Exception as e:
        log_fail("Error testing geometry utilities", str(e))

# ===== MAIN =====

def main():
    """Run all tests."""
    
    print("\n" + "="*70)
    print("  OVERWATCH — ZONE EDITOR FEATURE TESTING (Direct DB)")
    print("  Database & Service Logic Validation")
    print("="*70)
    
    section("INITIALIZATION")
    setup_database()
    cleanup_all_zones()
    
    section("STEP 1: ZONE CRUD OPERATIONS")
    zone_id = test_zone_creation()
    if zone_id:
        zone = test_zone_retrieval(zone_id)
        test_zone_deletion(zone_id)
    
    section("STEP 2: DATABASE VERIFICATION")
    test_database_structure()
    test_coordinate_normalization()
    
    section("STEP 3: CACHE & SERVICE")
    test_zone_service_loading()
    test_zone_service_caching()
    
    section("STEP 4: GEOMETRY UTILITIES")
    test_geometry_utilities()
    
    section("STEP 5: MULTIPLE ZONES")
    test_multiple_zones_independent()
    
    section("STEP 6: EDGE CASES")
    test_edge_cases()
    
    # Clean up
    cleanup_all_zones()
    
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
        print(f"\n✓ No bugs found in database/service layer!")
    
    success_rate = (TESTS_PASSED / (TESTS_PASSED + TESTS_FAILED) * 100) if (TESTS_PASSED + TESTS_FAILED) > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    print("\n" + "="*70)
    print("  Database & Service Testing Complete")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
