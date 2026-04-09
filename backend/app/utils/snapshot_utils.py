"""
OVERWATCH — Snapshot Path Utilities
===================================
Helpers for normalizing snapshot paths and constructing
stable public snapshot URLs.
"""

from pathlib import PurePosixPath
from typing import Optional


def extract_snapshot_filename(snapshot_path: Optional[str]) -> str:
    """Return a safe filename from a stored snapshot path string."""
    if not snapshot_path:
        return ""

    normalized = str(snapshot_path).strip().replace("\\", "/")
    normalized = normalized.split("?", 1)[0].split("#", 1)[0]
    filename = PurePosixPath(normalized).name

    if filename in {"", ".", ".."}:
        return ""

    return filename


def build_snapshot_url(snapshot_filename: str) -> str:
    """Return a relative API URL for a snapshot filename."""
    if not snapshot_filename:
        return ""
    return f"/snapshots/{snapshot_filename}"
