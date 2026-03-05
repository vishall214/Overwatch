"""
OVERWATCH — FastAPI Application Entrypoint
=============================================
Main application module that wires together all services,
registers API routes, and manages application lifecycle.

Run:
    cd backend
    uvicorn app.main:app --reload --port 8000

API Docs:
    http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logger import setup_logging
from app.core.dependencies import get_cached_settings, get_event_bus, get_pipeline_queues
from app.api.routes_camera import router as camera_router, init_camera_services
from app.api.routes_alerts import router as alerts_router
from app.api.routes_faces import router as faces_router

# ── Initialize logging early ────────────────────────────────────
setup_logging(level="INFO")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Initializes services on startup and cleans up on shutdown.
    Uses FastAPI's modern lifespan context manager pattern.

    Args:
        app: The FastAPI application instance.
    """
    # ── Startup ──────────────────────────────────────────────────
    settings = get_cached_settings()
    event_bus = get_event_bus()
    queues = get_pipeline_queues()

    logger.info("=" * 60)
    logger.info("  OVERWATCH v%s starting up", settings.app_version)
    logger.info("=" * 60)

    # Initialize camera services and pipeline
    pipeline = init_camera_services(settings, event_bus, queues)
    logger.info("All services initialized")

    yield

    # ── Shutdown ─────────────────────────────────────────────────
    logger.info("OVERWATCH shutting down...")

    # Stop pipeline if running
    if pipeline.is_running:
        await pipeline.stop()

    logger.info("OVERWATCH shutdown complete")


def create_app() -> FastAPI:
    """
    Application factory function.

    Creates and configures the FastAPI application with all
    middleware, routes, and lifecycle handlers.

    Returns:
        FastAPI: Configured application instance.
    """
    settings = get_cached_settings()

    application = FastAPI(
        title=settings.app_name,
        description="AI/ML-based real-time video surveillance analysis system",
        version=settings.app_version,
        lifespan=lifespan,
    )

    # ── CORS Middleware ──────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register Routes ──────────────────────────────────────────
    application.include_router(camera_router)
    application.include_router(alerts_router)
    application.include_router(faces_router)

    # ── Health Check ─────────────────────────────────────────────
    @application.get("/health", tags=["System"])
    async def health() -> dict:
        """Health check endpoint."""
        return {"status": "ok", "version": settings.app_version}

    return application


# ── Create the app instance ──────────────────────────────────────
app = create_app()
