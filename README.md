# OVERWATCH
AI/ML-Based Video Analysis and Interpretation System

## Quick Start

### 1. Full Stack with Docker (Frontend + Backend + Postgres + Redis)
```
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend Docs: http://localhost:8000/docs

Stop all services:
```
docker compose down
```

### 1.1 Publish Images to Docker Hub (to get shareable image links)
```powershell
docker login
docker build -t <your-dockerhub-username>/backend:latest ./backend
docker build -t <your-dockerhub-username>/frontend:latest ./frontend
docker push <your-dockerhub-username>/backend:latest
docker push <your-dockerhub-username>/frontend:latest
```

After push, your image pages are:
- Backend: https://hub.docker.com/repository/docker/<your-dockerhub-username>/backend/general
- Frontend: https://hub.docker.com/repository/docker/<your-dockerhub-username>/frontend/general

### 2. Local Development (without Docker for app services)

Start infra only:
```
docker compose up -d postgres redis
```

Backend:
```
cd backend
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt   # optional: tests / dev tooling
uvicorn app.main:app --reload --port 8000
```
API: http://localhost:8000
Docs: http://localhost:8000/docs

Frontend:
```
cd frontend
npm install
npm run dev
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
