"""
OVERWATCH — Database CRUD Operations
========================================
Functions for creating and querying alert records.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import heapq
import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import AlertRow, FaceRow, Zone, User

logger = logging.getLogger(__name__)

_MAX_RANGE_HOURS = 24 * 30


def _extract_threat_context(metadata: Optional[dict]) -> tuple[int, str]:
    """Return (score, level) from alert metadata with safe defaults."""
    if not isinstance(metadata, dict):
        return 0, "LOW"

    raw_score = metadata.get("threat_score", 0)
    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        score = 0

    raw_level = str(metadata.get("threat_level", "LOW")).upper()
    if raw_level not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raw_level = "LOW"

    return max(0, score), raw_level


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

    if range_hours < 1 or range_hours > _MAX_RANGE_HOURS:
        range_hours = 1

    cutoff = datetime.now(timezone.utc) - timedelta(hours=range_hours)

    rows = (
        db.query(AlertRow.timestamp)
        .filter(AlertRow.timestamp >= cutoff)
        .order_by(AlertRow.timestamp.asc())
        .all()
    )

    def _to_utc(ts: datetime) -> datetime:
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    bucket_counts: dict[datetime, int] = defaultdict(int)
    for (timestamp,) in rows:
        if timestamp is None:
            continue
        ts = _to_utc(timestamp)
        if interval == "hour":
            bucket = ts.replace(minute=0, second=0, microsecond=0)
        else:
            bucket = ts.replace(second=0, microsecond=0)
        bucket_counts[bucket] += 1

    now = datetime.now(timezone.utc)
    if interval == "hour":
        cursor = cutoff.replace(minute=0, second=0, microsecond=0)
        end = now.replace(minute=0, second=0, microsecond=0)
        step = timedelta(hours=1)
    else:
        cursor = cutoff.replace(second=0, microsecond=0)
        end = now.replace(second=0, microsecond=0)
        step = timedelta(minutes=1)

    points: list[dict] = []
    while cursor <= end:
        points.append(
            {
                "time": cursor.isoformat(),
                "count": int(bucket_counts.get(cursor, 0)),
            }
        )
        cursor += step

    return points


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
    if range_hours < 1 or range_hours > _MAX_RANGE_HOURS:
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
) -> dict[str, int | float]:
    """
    Get summary of alerts by type and total count.

    Args:
        db: Database session.
        range_hours: Time window in hours (default: 24).

    Returns:
        Dict with total, intrusion, loitering, crowd, weapon and face counts.
    """
    if range_hours < 1 or range_hours > _MAX_RANGE_HOURS:
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

    threat = get_threat_metrics(db, range_hours, peak_limit=1)

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
        "avg_threat_score": float(threat["avg_threat_score"]),
        "peak_threat_score": int(threat["peak_threat_score"]),
    }


def get_threat_metrics(
    db: Session,
    range_hours: int = 24,
    peak_limit: int = 5,
) -> dict:
    """Aggregate threat-level distribution, average threat score, and peak threat events."""
    if range_hours < 1 or range_hours > _MAX_RANGE_HOURS:
        range_hours = 24
    if peak_limit < 1:
        peak_limit = 1

    cutoff = datetime.now(timezone.utc) - timedelta(hours=range_hours)
    rows = (
        db.query(
            AlertRow.id,
            AlertRow.event_type,
            AlertRow.zone,
            AlertRow.timestamp,
            AlertRow.metadata_,
        )
        .filter(AlertRow.timestamp >= cutoff)
        .all()
    )

    distribution = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
    }
    scored_events: list[dict] = []

    for row in rows:
        score, level = _extract_threat_context(row.metadata_)
        distribution[level] = distribution.get(level, 0) + 1
        scored_events.append(
            {
                "id": row.id,
                "event_type": row.event_type,
                "zone": row.zone or "",
                "timestamp": row.timestamp.isoformat() if row.timestamp else "",
                "threat_score": score,
                "threat_level": level,
            }
        )

    avg_score = 0.0
    if scored_events:
        avg_score = round(
            sum(event["threat_score"] for event in scored_events) / len(scored_events),
            1,
        )

    peak_events = heapq.nlargest(
        peak_limit,
        scored_events,
        key=lambda event: (
            int(event["threat_score"]),
            str(event["timestamp"]),
        ),
    )

    peak_score = peak_events[0]["threat_score"] if peak_events else 0

    return {
        "distribution": distribution,
        "avg_threat_score": avg_score,
        "peak_threat_score": peak_score,
        "peak_events": peak_events,
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


def get_all_user_emails(db: Session) -> list[str]:
    """Return email addresses of all registered users."""
    rows = db.query(User.email).all()
    return [row[0] for row in rows if row[0]]
