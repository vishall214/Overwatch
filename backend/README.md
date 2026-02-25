# OVERWATCH — Backend

FastAPI backend for the OVERWATCH surveillance analysis system.

## Setup
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app:app --reload --port 8000
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## API Overview

| Method | Path | Phase | Description |
|--------|------|-------|-------------|
| GET | /health | 1 | System health check |
| GET | /cameras | 1 | List all cameras |
| POST | /cameras | 1 | Register a new camera |
| POST | /cameras/{id}/start | 2 | Start video pipeline |
| POST | /cameras/{id}/stop | 2 | Stop video pipeline |
| GET | /events | 3 | List detection events |
| GET | /events/{id} | 3 | Get event with snapshot |
| GET | /alerts | 6 | List alerts |
| PATCH | /alerts/{id}/acknowledge | 6 | Acknowledge alert |
| PATCH | /alerts/{id}/resolve | 6 | Resolve alert |
| WS | /ws/alerts | 6 | Real-time alert stream |
| GET | /stream/{id} | 2 | MJPEG live camera feed |
| GET | /faces | 5 | List enrolled identities |
| POST | /faces/enroll | 5 | Enroll a new face |
| DELETE | /faces/{name} | 5 | Remove an identity |
| GET | /reports | 7 | List generated reports |
| POST | /reports/generate | 7 | Generate a report |

## How the codebase grows
```
Phase 1:  app.py              (everything in one file)
Phase 3+: app.py              (routes only, extract when it gets long)
          config.py           (settings)
          database.py         (models + session)
          services/
            pipeline.py       (video loop)
            detector.py       (YOLO)
            tracker.py        (ByteTrack)
            behavior.py       (loitering, zones)
            recognizer.py     (InsightFace + FAISS)
            alert_engine.py   (cooldown + Redis publish)
```
