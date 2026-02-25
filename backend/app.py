"""
OVERWATCH - Backend Entry Point
================================
Start here.Everything lives in this file until the codebase demands splitting.

Run:
    uvicorn app:app --reload --port 8000

API Docs:
    http://localhost:8000/docs
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────
app = FastAPI(
    title="OVERWATCH",
    description="AI/ML-based surveillance video analysis system",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ─────────────────────────────────────────────
# Cameras  (stub — implement in Phase 1)
# ─────────────────────────────────────────────
@app.get("/cameras", tags=["Cameras"])
async def list_cameras():
    # TODO: query DB, return list of camera records
    return {"cameras": []}


@app.post("/cameras", tags=["Cameras"])
async def add_camera(name: str, feed_url: str, camera_type: str = "cctv"):
    # TODO: validate, insert into DB, return created camera
    # camera_type: "cctv" | "drone" | "bodycam" | "robot"
    return {"message": "TODO", "name": name, "feed_url": feed_url}


@app.post("/cameras/{camera_id}/start", tags=["Cameras"])
async def start_camera(camera_id: int):
    # TODO: launch VideoPipeline task for this camera
    return {"message": f"TODO: start camera {camera_id}"}


@app.post("/cameras/{camera_id}/stop", tags=["Cameras"])
async def stop_camera(camera_id: int):
    # TODO: stop VideoPipeline task for this camera
    return {"message": f"TODO: stop camera {camera_id}"}


# ─────────────────────────────────────────────
# Events  (stub — implement in Phase 3)
# ─────────────────────────────────────────────
@app.get("/events", tags=["Events"])
async def list_events(camera_id: int = None, event_type: str = None, limit: int = 50):
    # TODO: query events table with optional filters
    # event_type: person_detected | weapon_detected | face_recognized |
    #             loitering | zone_intrusion | abandoned_object
    return {"events": [], "total": 0}


@app.get("/events/{event_id}", tags=["Events"])
async def get_event(event_id: int):
    # TODO: return event + snapshot path + clip path
    return {"event_id": event_id, "message": "TODO"}


# ─────────────────────────────────────────────
# Alerts  (stub — implement in Phase 6)
# ─────────────────────────────────────────────
@app.get("/alerts", tags=["Alerts"])
async def list_alerts(status: str = None, severity: str = None):
    # TODO: query alerts table
    # status: new | acknowledged | resolved | false_positive
    # severity: low | medium | high | critical
    return {"alerts": []}


@app.patch("/alerts/{alert_id}/acknowledge", tags=["Alerts"])
async def acknowledge_alert(alert_id: int):
    # TODO: set status=acknowledged, record who + when
    return {"message": f"TODO: acknowledge {alert_id}"}


@app.patch("/alerts/{alert_id}/resolve", tags=["Alerts"])
async def resolve_alert(alert_id: int):
    # TODO: set status=resolved
    return {"message": f"TODO: resolve {alert_id}"}


# ─────────────────────────────────────────────
# Streams  (stub — implement in Phase 2)
# ─────────────────────────────────────────────
@app.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    """
    Real-time alert push to dashboard clients.
    Phase 6: subscribe to Redis pub/sub channel 'alerts', forward to client.
    """
    await websocket.accept()
    try:
        # TODO: connect to Redis pubsub, forward messages
        await websocket.send_json({"status": "connected", "message": "TODO: wire Redis"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass


@app.get("/stream/{camera_id}", tags=["Streams"])
async def mjpeg_stream(camera_id: int):
    """
    Phase 2: Return StreamingResponse of annotated JPEG frames.
    """
    return {"message": f"TODO: MJPEG stream for camera {camera_id}"}


# ─────────────────────────────────────────────
# Face DB  (stub — implement in Phase 5)
# ─────────────────────────────────────────────
@app.get("/faces", tags=["Face DB"])
async def list_enrolled_faces():
    # TODO: return list of enrolled identities from FAISS label store
    return {"identities": []}


@app.post("/faces/enroll", tags=["Face DB"])
async def enroll_face(name: str):
    # TODO: accept image upload, extract ArcFace embedding, add to FAISS index
    return {"message": f"TODO: enroll {name}"}


@app.delete("/faces/{name}", tags=["Face DB"])
async def remove_face(name: str):
    # TODO: remove identity from FAISS index and label store
    return {"message": f"TODO: remove {name}"}


# ─────────────────────────────────────────────
# Reports  (stub — implement in Phase 7)
# ─────────────────────────────────────────────
@app.get("/reports", tags=["Reports"])
async def list_reports():
    # TODO: return generated report files from data/outputs/reports/
    return {"reports": []}


@app.post("/reports/generate", tags=["Reports"])
async def generate_report(from_date: str, to_date: str):
    # TODO: query events+alerts in range, build PDF/JSON summary
    return {"message": "TODO: generate report", "from": from_date, "to": to_date}
