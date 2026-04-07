"""
OVERWATCH — Database CRUD Operations
========================================
Functions for creating and querying alert records.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .models import AlertRow, FaceRow, Zone, User

logger = logging.getLogger(__name__)


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
    logger.info(
        "ZONE DB INSERT REQUEST: type=%s x=%.4f y=%.4f w=%.4f h=%.4f camera_id=%s",
        zone_type,
        x,
        y,
        width,
        height,
        camera_id,
    )
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
    logger.info(
        "ZONE DB INSERTED: id=%d type=%s x=%.4f y=%.4f w=%.4f h=%.4f",
        row.id,
        row.type,
        row.x,
        row.y,
        row.width,
        row.height,
    )
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


# ── Analytics CRUD ────────────────────────────────────────────────


def get_alerts_over_time(
    db: Session,
    interval: str = "minute",
    range_hours: int = 1,
) -> list[dict]:
    """
    Get alert counts grouped by time interval.

    Uses SQL aggregation with GROUP BY for performance.

    Args:
        db: Database session.
        interval: "minute" or "hour" (default: minute).
        range_hours: Time window in hours (default: 1).

    Returns:
        List of dicts with 'time' and 'count' keys.
    """
    if interval not in ["minute", "hour"]:
        interval = "minute"

    if range_hours < 1 or range_hours > 24:
        range_hours = 1

    # Determine SQL date truncation
    trunc_str = f"'{interval}'" if interval else "'minute'"
    interval_sql = f"DATE_TRUNC({trunc_str}, timestamp)"

    # Build query with parameterized time window
    cutoff = datetime.now(timezone.utc) - timedelta(hours=range_hours)

    query = f"""
        SELECT
            {interval_sql} AS bucket,
            COUNT(*) as count
        FROM alerts
        WHERE timestamp >= :cutoff
        GROUP BY bucket
        ORDER BY bucket ASC
    """

    rows = db.execute(
        text(query),
        {"cutoff": cutoff},
    ).fetchall()

    return [
        {
            "time": row[0].isoformat() if row[0] else "",
            "count": row[1],
        }
        for row in rows
    ]


def get_event_distribution(
    db: Session,
    range_hours: int = 24,
) -> dict[str, int]:
    """
    Get alert counts grouped by event type.

    Uses SQL aggregation for performance.

    Args:
        db: Database session.
        range_hours: Time window in hours (default: 24).

    Returns:
        Dict with event_type as key and count as value.
    """
    if range_hours < 1 or range_hours > 24:
        range_hours = 24

    cutoff = datetime.now(timezone.utc) - timedelta(hours=range_hours)

    rows = (
        db.query(
            AlertRow.event_type,
            func.count(AlertRow.id).label("count"),
        )
        .filter(AlertRow.timestamp >= cutoff)
        .group_by(AlertRow.event_type)
        .all()
    )

    return {row[0]: row[1] for row in rows}


def get_alert_summary(
    db: Session,
    range_hours: int = 24,
) -> dict[str, int]:
    """
    Get summary of alerts by type and total count.

    Args:
        db: Database session.
        range_hours: Time window in hours (default: 24).

    Returns:
        Dict with total, intrusion, loitering, crowd, weapon and face counts.
    """
    if range_hours < 1 or range_hours > 24:
        range_hours = 24

    cutoff = datetime.now(timezone.utc) - timedelta(hours=range_hours)

    # Total count
    total = db.query(func.count(AlertRow.id)).filter(
        AlertRow.timestamp >= cutoff
    ).scalar() or 0

    # Distribution by type
    distribution = get_event_distribution(db, range_hours)
    legacy_weapon = distribution.get("dangerous_object", 0)
    weapon_detected = distribution.get("weapon_detected", 0) + legacy_weapon
    weapon_in_zone = distribution.get("weapon_in_zone", 0)
    weapon_total = weapon_detected + weapon_in_zone

    return {
        "total": total,
        "intrusion": distribution.get("intrusion", 0),
        "loitering": distribution.get("loitering", 0),
        "crowd": distribution.get("crowd", 0),
        "weapon_detected": weapon_detected,
        "weapon_in_zone": weapon_in_zone,
        # Keep legacy key for backward compatibility with older clients.
        "dangerous_object": weapon_total,
        "face_match": distribution.get("face_match", 0),
    }


# ── Auth CRUD ─────────────────────────────────────────────────────


def get_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by unique email."""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, email: str, password_hash: str) -> User:
    """Create and persist a new user record."""
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
