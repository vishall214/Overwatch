"""
OVERWATCH — Database CRUD Operations
========================================
Functions for creating and querying alert records.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from .models import AlertRow, FaceRow, Zone


def create_alert_row(
    db: Session,
    event_type: str,
    track_id: Optional[int] = None,
    zone: Optional[str] = None,
    snapshot_path: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AlertRow:
    """Insert a new alert row and return it."""
    row = AlertRow(
        event_type=event_type,
        track_id=track_id,
        zone=zone,
        timestamp=datetime.now(timezone.utc),
        snapshot_path=snapshot_path or "",
        metadata_=metadata,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_recent_alerts(db: Session, limit: int = 50) -> list[AlertRow]:
    """Return the most recent alerts, newest first."""
    return (
        db.query(AlertRow)
        .order_by(AlertRow.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_alert_count(db: Session) -> int:
    """Return total number of alerts."""
    return db.query(AlertRow).count()


# ── Face CRUD ────────────────────────────────────────────────────


def create_face_row(
    db: Session,
    name: str,
    embedding: list[float],
) -> FaceRow:
    """Insert a new watchlist face and return the row."""
    row = FaceRow(
        name=name,
        embedding=embedding,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_all_faces(db: Session) -> list[FaceRow]:
    """Return all watchlist faces."""
    return db.query(FaceRow).order_by(FaceRow.created_at.desc()).all()


def delete_face_by_name(db: Session, name: str) -> bool:
    """Delete a face by name. Returns True if a row was deleted."""
    row = db.query(FaceRow).filter(FaceRow.name == name).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Zone CRUD ────────────────────────────────────────────────────


def create_zone(
    db: Session,
    zone_type: str,
    x: float,
    y: float,
    width: float,
    height: float,
    name: Optional[str] = None,
    camera_id: str = "default",
) -> Zone:
    """Insert a new zone and return it."""
    row = Zone(
        name=name,
        type=zone_type,
        x=x,
        y=y,
        width=width,
        height=height,
        camera_id=camera_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_zones(db: Session) -> list[Zone]:
    """Return all active zones."""
    return db.query(Zone).filter(Zone.is_active == True).all()  # noqa: E712


def delete_zone(db: Session, zone_id: int) -> bool:
    """Delete a zone by ID. Returns True if a row was deleted."""
    row = db.query(Zone).filter(Zone.id == zone_id).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True

