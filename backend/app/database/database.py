"""
OVERWATCH — Database Engine & Session
=========================================
Manages the SQLAlchemy engine and session factory.
Connection string is loaded from the DATABASE_URL environment variable.
Falls back to SQLite if DATABASE_URL is not set or Postgres is unavailable.
"""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

logger = logging.getLogger(__name__)

_DATABASE_URL: str | None = os.getenv("DATABASE_URL")
_SQLITE_FALLBACK: str = "sqlite:///./overwatch.db"


def _make_engine(url: str) -> Engine:
    """Create a SQLAlchemy engine with sensible defaults for the given URL."""
    connect_args: dict[str, Any] = (
        {"check_same_thread": False} if url.startswith("sqlite") else {}
    )
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


def _resolve_engine() -> Engine:
    """
    Try the configured DATABASE_URL first.
    If it is unset, unreachable, or the connection fails, fall back to SQLite.
    """
    if _DATABASE_URL:
        try:
            eng = _make_engine(_DATABASE_URL)
            # Fast connectivity check — raises OperationalError if Postgres is down
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connected: %s", _DATABASE_URL)
            return eng
        except OperationalError as exc:
            logger.warning(
                "Could not connect to DATABASE_URL (%s). "
                "Falling back to SQLite: %s",
                exc.__class__.__name__,
                _SQLITE_FALLBACK,
            )
    else:
        logger.warning(
            "DATABASE_URL is not set. Falling back to SQLite: %s",
            _SQLITE_FALLBACK,
        )

    eng = _make_engine(_SQLITE_FALLBACK)
    logger.info("Database connected (SQLite fallback): %s", _SQLITE_FALLBACK)
    return eng


engine: Engine = _resolve_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
