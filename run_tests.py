"""
Run zone editor tests without PostgreSQL dependency.
Forces SQLite fallback by temporarily unsetting DATABASE_URL.
"""
import os
import sys
import subprocess

# Force SQLite fallback
os.environ.pop("DATABASE_URL", None)

# Run the direct database tests
result = subprocess.run([sys.executable, "test_zone_direct.py"], cwd="c:\\Users\\visha\\Desktop\\Overwatch")
sys.exit(result.returncode)
