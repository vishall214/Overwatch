"""
OVERWATCH — Database Models
===============================
SQLAlchemy ORM table definitions.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String

from .database import Base


class Zone(Base):
    """User-defined rectangular zone for behavior analysis."""

    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    type = Column(String, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    camera_id = Column(String, default="default")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertRow(Base):
    """Persistent alert record stored in PostgreSQL."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    track_id = Column(Integer, nullable=True)
    zone = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    snapshot_path = Column(String, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)


class FaceRow(Base):
    """Watchlist face embedding stored in PostgreSQL."""

    __tablename__ = "faces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    embedding = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    """Application user for JWT authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
