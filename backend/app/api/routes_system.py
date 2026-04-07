"""
OVERWATCH — System Control & Monitoring API Routes
=====================================================
Endpoints for querying and dynamically enabling or disabling
analytics modules, and for reading pipeline metrics and alert
statistics.

Routes:
    GET  /system/modules                    — list all module states
    POST /system/modules/{name}/enable      — enable a module
    POST /system/modules/{name}/disable     — disable a module
    GET  /system/status                     — combined system health
    GET  /system/metrics                    — detailed pipeline metrics
    GET  /system/alerts/stats               — alert count breakdown
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services.module_controller import ModuleController, SUPPORTED_MODULES
from app.services.system_monitor import SystemMonitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System"])

# ── Service singletons (set during startup via init_system_routes) ──
_module_controller: Optional[ModuleController] = None
_pipeline_ref = None  # VideoPipeline reference for /system/status
_system_monitor: Optional[SystemMonitor] = None


def init_system_routes(
    module_controller: ModuleController,
    pipeline=None,
    system_monitor: Optional[SystemMonitor] = None,
) -> None:
    """
    Inject the ModuleController, pipeline, and SystemMonitor singletons.

    Called once during application startup by init_camera_services.

    Args:
        module_controller: Shared module state controller.
        pipeline: Optional VideoPipeline for camera_running status.
        system_monitor: Optional SystemMonitor for metrics endpoints.
    """
    global _module_controller, _pipeline_ref, _system_monitor
    _module_controller = module_controller
    _pipeline_ref = pipeline
    _system_monitor = system_monitor
    logger.info("System routes initialized")


def _get_controller() -> ModuleController:
    if _module_controller is None:
        raise HTTPException(
            status_code=503,
            detail="System controller not initialized",
        )
    return _module_controller


# ─────────────────────────────────────────────────────────────────
# GET /system/modules
# ─────────────────────────────────────────────────────────────────

@router.get("/modules")
async def get_modules() -> dict:
    """
    Return the current enabled/disabled state of all analytics modules.

    Response example::

        {
          "intrusion": true,
          "loitering": true,
          "crowd": true,
          "weapon_detection": true
        }
    """
    return _get_controller().modules


# ─────────────────────────────────────────────────────────────────
# POST /system/modules/{name}/enable
# ─────────────────────────────────────────────────────────────────

@router.post("/modules/{name}/enable")
async def enable_module(name: str) -> dict:
    """
    Enable an analytics module by name.

    Valid names: intrusion, loitering, crowd, weapon_detection.
    """
    ctrl = _get_controller()
    if name not in SUPPORTED_MODULES:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown module '{name}'. "
                f"Valid modules: {sorted(SUPPORTED_MODULES)}"
            ),
        )
    ctrl.enable(name)
    return {"module": name, "enabled": True, "modules": ctrl.modules}


# ─────────────────────────────────────────────────────────────────
# POST /system/modules/{name}/disable
# ─────────────────────────────────────────────────────────────────

@router.post("/modules/{name}/disable")
async def disable_module(name: str) -> dict:
    """
    Disable an analytics module by name.

    Valid names: intrusion, loitering, crowd, weapon_detection.
    """
    ctrl = _get_controller()
    if name not in SUPPORTED_MODULES:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown module '{name}'. "
                f"Valid modules: {sorted(SUPPORTED_MODULES)}"
            ),
        )
    ctrl.disable(name)
    return {"module": name, "enabled": False, "modules": ctrl.modules}


# ─────────────────────────────────────────────────────────────────
# GET /system/status
# ─────────────────────────────────────────────────────────────────

@router.get("/status")
async def system_status() -> dict:
    """
        Return combined system health, pipeline FPS, active module
        states, and total alert count.

        Response example::

                {
                    "camera_running": true,
                    "pipeline_fps": 4.8,
                    "active_modules": {
                        "intrusion": true,
                        "loitering": false,
                        "crowd": true,
                        "weapon_detection": true
                    },
                    "alerts_total": 42
                }
    """
    if _system_monitor is not None:
        return _system_monitor.get_system_status()

    # Fallback when SystemMonitor is not injected
    ctrl = _get_controller()
    camera_running = False
    if _pipeline_ref is not None:
        camera_running = _pipeline_ref.is_running
    return {
        "camera_running": camera_running,
        "pipeline_fps": 0.0,
        "active_modules": ctrl.modules,
        "alerts_total": 0,
    }


# ─────────────────────────────────────────────────────────────────
# GET /system/metrics
# ─────────────────────────────────────────────────────────────────

@router.get("/metrics")
async def pipeline_metrics() -> dict:
    """
    Return detailed per-stage pipeline performance metrics
    and queue fill levels.

    Response example::

        {
          "capture": { "frames_captured": 1200, ... },
          "inference": { "avg_inference_ms": 210, ... },
          "tracking": { ... },
          "behavior": { ... },
          "stream": { ... },
          "queues": { "frame_queue": 1, ... }
        }
    """
    if _system_monitor is None:
        raise HTTPException(
            status_code=503,
            detail="System monitor not initialized",
        )
    return _system_monitor.get_pipeline_metrics()


# ─────────────────────────────────────────────────────────────────
# GET /system/alerts/stats
# ─────────────────────────────────────────────────────────────────

@router.get("/alerts/stats")
async def alert_stats() -> dict:
    """
    Return aggregated alert counts grouped by event type.

    Response example::

        {
          "total_alerts": 42,
          "intrusion": 20,
          "loitering": 15,
          "crowd": 7,
                    "weapon_detected": 2,
                    "weapon_in_zone": 1,
                    "dangerous_object": 3,
          "face_match": 0
        }
    """
    if _system_monitor is None:
        raise HTTPException(
            status_code=503,
            detail="System monitor not initialized",
        )
    return _system_monitor.get_alert_stats()
