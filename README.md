# OVERWATCH
AI/ML-Based Video Analysis and Interpretation System

## Quick Start

### 1. Infrastructure
```
docker compose up -d
```

### 2. Backend
```
cd backend
.venv\Scripts\Activate.ps1
uvicorn app:app --reload --port 8000
```
API: http://localhost:8000
Docs: http://localhost:8000/docs

### 3. Frontend
```
cd frontend
npm start
```
App: http://localhost:3000

## Structure
```
overwatch/
├── backend/
│   ├── app.py              <- Entire API, grows then splits
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   └── README.md
├── data/
│   ├── samples/            <- Test videos (git-ignored)
│   └── outputs/            <- Snapshots, clips, reports (git-ignored)
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Phases

| Phase | What | Week |
|-------|------|------|
| 1 | Camera CRUD + DB + React scaffold | 1-2 |
| 2 | Video ingestion + MJPEG stream | 3 |
| 3 | YOLOv8 detection + ByteTrack | 4-5 |
| 4 | Behavior analysis (loitering, zones) | 6 |
| 5 | Face recognition (InsightFace + FAISS) | 7 |
| 6 | Alerts + WebSocket dashboard | 8 |
| 7 | Investigation tools + reports | 9 |
| 8 | Polish + demo | 10 |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| Detection | YOLOv8 |
| Tracking | ByteTrack |
| Face Recognition | InsightFace + FAISS |
| Video | OpenCV + FFmpeg |
| Database | PostgreSQL + SQLAlchemy |
| Messaging | Redis + WebSocket |
| Frontend | React + Tailwind CSS |
| Infra | Docker Compose |
