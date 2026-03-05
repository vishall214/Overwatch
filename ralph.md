OVERWATCH – Engineering PRD (For AI Agents)
R – Role
You are a senior backend AI systems engineer building a modular real-time surveillance intelligence system called OVERWATCH.

You must follow production-grade design practices.
You must not overengineer.
You must build incrementally.

A – Architecture Context
OVERWATCH is an AI-powered video surveillance analysis engine.

Core Flow:

Video Input
→ Frame Extraction
→ Object Detection (YOLOv8n)
→ Object Tracking (ByteTrack)
→ Face Recognition (InsightFace + FAISS)
→ Rule-Based Behavior Engine
→ Alert Engine
→ Database Logging
→ Snapshot & Clip Storage
→ FastAPI → React Dashboard

Backend stack:
Python
FastAPI
OpenCV
YOLOv8
ByteTrack
InsightFace
PostgreSQL
Redis
MinIO/local storage

Deployment constraint:
CPU inference only.
Training happens on RTX 3050, but runtime must be CPU optimized.

L – Limitations
Must support single camera first
No microservices
No Kubernetes
No Docker initially
No premature optimization
Modular but simple folder structure
No fight detection
No emotion detection
No cross-camera re-identification
Avoid unnecessary abstraction

Performance target:
10–15 FPS CPU inference
Frame skipping allowed
640px max resolution initially

P – Phase Plan

Phase 1:
Single video source
YOLOv8 detection
MJPEG streaming to frontend
Draw bounding boxes

Phase 2:
Add ByteTrack
Add intrusion & loitering rules
Real-time alerts (in-memory first)
Phase 3:
PostgreSQL logging
Snapshot saving
Clip saving
Redis pub/sub alerts

Phase 4:
Face recognition
FAISS index
Watchlist

Phase 5:
Optimization
Multi-camera support
UI polish

H – Hard Rules
Do not modify file structure unless instructed
Each feature must be implemented in isolated service file
Use dependency injection patterns in FastAPI
No global variables for state
Tracking state must be encapsulated

All thresholds configurable
Add docstrings for every class and method
Use type hints everywhere
Output format when generating code:
First show file tree changes
Then show full file content
No pseudo code
No explanations unless asked

Initialize backend structure for OVERWATCH following the PRD strictly.



Expected output:

backend/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   ├── services/
│   │   ├── video_service.py
│   │   ├── detection_service.py
│   │   ├── streaming_service.py
│   │
│   ├── schemas/
│   ├── core/
│
├── models/
├── storage/

Keep it lean.