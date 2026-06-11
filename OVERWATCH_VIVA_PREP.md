# OVERWATCH Viva Preparation Document
Date: April 29, 2026

## How to use this document
- Start with the scripts (Section 16).
- Skim headings for recall, then drill into the sections you struggle with.
- Use the Keywords section for last-minute revision.

## One-line summary
OVERWATCH is a CPU-first, real-time AI surveillance pipeline that turns raw video streams into structured security alerts using YOLOv8 detection, ByteTrack tracking, rule-based behavior analysis, and a FastAPI + React monitoring stack.

## At a glance
| Item | Summary |
| --- | --- |
| System type | Real-time, edge-friendly, CPU-optimized video analytics |
| Core pipeline | Capture -> Detection -> Tracking -> Behavior -> Alerts/Storage/Stream |
| Primary outputs | Alerts, snapshots, reports, live annotated MJPEG stream |
| Backend | FastAPI, SQLAlchemy, PostgreSQL (SQLite fallback) |
| Frontend | React, Vite, Tailwind CSS |

## 1) Project Overview
- Problem: manual monitoring of multiple feeds causes missed events and slow response.
- Why it matters: low-latency, explainable alerts reduce alert fatigue and speed response.
- Applications: control rooms, perimeters, campuses, industrial sites, public events.
- System type: multi-stage, asynchronous video analytics with bounded queues.

Scope status
- Implemented: detection, tracking, intrusion/loitering/crowd logic, weapon detection pipeline, alert persistence, snapshots, reporting, monitoring metrics.
- Optional: face recognition (InsightFace + FAISS).
- Planned: abandoned object and speed anomaly modules; richer alert streaming.

## 2) Core Technologies (What + Why)
YOLOv8n (object detection)
- What: one-stage detector predicting boxes and classes in one forward pass.
- Why: best CPU speed/accuracy tradeoff; Faster R-CNN is slower, SSD is less accurate on small or occluded targets.

ByteTrack (multi-object tracking)
- What: tracker that uses high- and low-confidence detections for association.
- Why: stronger ID continuity than SORT; lighter compute than DeepSORT.

FastAPI (backend)
- What: async Python web framework with automatic OpenAPI docs.
- Why: high performance and clean dependency injection for real-time services.

React + Vite (frontend)
- What: SPA for monitoring, analytics, and reporting.
- Why: fast dev workflow and easy MJPEG integration.

PostgreSQL (database)
- What: relational DB for alerts, zones, users, watchlist faces.
- Why: indexing, JSON metadata, durable audit trails; SQLite fallback for local dev.

OpenCV + FFmpeg
- What: video capture, resize, and JPEG encoding.
- Why: mature and reliable CPU video I/O stack.

Optimization techniques
- Asynchronous pipeline workers
- Bounded queues with drop-oldest behavior
- Configurable frame skipping
- Resolution caps for inference
- Separate weapon detection cadence
- Background threads for face recognition and alert persistence

## 3) End-to-End Architecture
Pipeline steps
1. Capture: SourceManager opens camera/demo/upload streams and reads frames.
2. Detection: YOLOv8n runs inference and produces detections per frame.
3. Tracking: ByteTrack assigns persistent IDs to detections.
4. Behavior: rule engine checks intrusion, loitering, crowd, and weapons.
5. Alerts + Storage: alerts persisted to DB; snapshots saved to disk.
6. Stream: annotated frames encoded as MJPEG for the UI.

Data flow (packets)
- FramePacket -> DetectionPacket -> TrackingPacket -> BehaviorPacket
- Packets carry timestamps and stage latencies for monitoring.

Threading and backpressure (why it stays real-time)
- Each stage runs in its own worker thread, so slow inference does not freeze capture or streaming.
- Bounded queues decouple producer/consumer speed; drop-oldest keeps frames fresh under load.
- Source pacing prevents file uploads from playing faster than the original FPS.

Event and control flow
- An internal EventBus publishes detection and behavior events without tight coupling.
- Module toggles (intrusion/loitering/crowd/weapon detection) are read once per frame to keep per-frame overhead minimal.
- The SystemMonitor aggregates queue depth and stage latency into dashboard metrics.

Why modular pipeline
- Isolates slow stages to avoid blocking
- Makes profiling and optimization easier
- Allows module toggling without restart
- Keeps the stream responsive under load

## 4) Key Components (What each does)
CaptureWorker
- Purpose: pull frames from SourceManager and feed the pipeline.
- Key function to mention: `CaptureWorker._capture_loop()` (frame read, skip/pacing, queue push).
- Output: FramePacket with capture timestamp.

InferenceWorker
- Purpose: run YOLOv8n detection and optional weapon detection cadence.
- Key function to mention: `InferenceWorker._inference_loop()` (runs detection, publishes event, queues DetectionPacket).
- Output: DetectionPacket with detections + inference timing.

TrackingWorker
- Purpose: stabilize identities across frames with ByteTrack.
- Key function to mention: `TrackingWorker._tracking_loop()` (association and annotated labels).
- Output: TrackingPacket with tracked objects and tracking timing.

BehaviorWorker
- Purpose: translate tracks into security events with rules and thresholds.
- Key functions to mention:
	- `BehaviorWorker._behavior_loop()` (zone logic and alert prep)
	- `BehaviorWorker._handle_weapon_detections()` (consecutive + cooldown logic)
	- `BehaviorWorker._compute_threat()` (threat score calculation)
- Output: BehaviorPacket + queued alerts.

AlertService
- Purpose: persist alerts and save snapshots without blocking the pipeline.
- Key function to mention: `AlertService.create_alert()` (dedup, snapshot, DB write).

ZoneService
- Purpose: cache zones in memory to avoid DB access inside the hot path.

ReportService + Scheduler
- Purpose: generate daily/weekly reports and optional email distribution.
- Key functions to mention: `ReportService.generate_report()` and `ReportScheduler.start()`.

SystemMonitor
- Purpose: aggregate live pipeline metrics and alert counts for the UI.
- Key function to mention: `SystemMonitor.get_system_status()` (FPS + alerts summary).

Auth/Security helpers (important to mention in viva)
- JWT login/signup and protected routes.
- Key function to mention: `get_current_user()` (token verification and authorization).

## 5) Behavior Logic (Rule-based and Explainable)
Intrusion
- A tracked person intersects an intrusion zone, then triggers after stability threshold and cooldown.
- Zone intersection uses normalized zone rectangles mapped to pixel space for fast checks.

Loitering
- Dwell time inside a zone exceeds threshold.
- Grace window avoids false resets from boundary flicker.

Crowd
- Per-zone person count exceeds threshold for enough frames.

Weapon detection
- Separate YOLO model; triggers only after consecutive confirmations.
- Two alert types: weapon_in_zone (critical) and weapon_detected (warning).
- Cooldown keys are scoped by class and zone to prevent repeated alerts for the same object.

Face recognition (optional)
- InsightFace embeddings, FAISS nearest-neighbor search, watchlist stored in DB.
- Runs on a separate worker thread to avoid blocking the main behavior loop.

## 6) Alerts, Deduplication, Threat Scoring
Alert generation
- BehaviorWorker queues alerts so DB and snapshot I/O never blocks analysis.
- AlertService persists alerts and saves snapshots.
- Snapshots are cleaned by retention rules to prevent disk bloat.

Deduplication layers
1) Stability thresholds (intrusion, crowd)
2) Per-event cooldowns
3) AlertService duplicate suppression window

Why three layers
- Stability stops single-frame noise.
- Cooldowns prevent bursts from the same object or zone.
- Final dedup removes near-duplicate alerts across frames.

Threat scoring
- Signals: weapon_detected, weapon_in_zone, intrusion, loitering, crowd
- Weighted sum with context bonuses
- Outputs: threat_score and threat_level (LOW/MEDIUM/HIGH/CRITICAL)

## 7) Concepts to Remember (Simple definitions)
- IoU: overlap score between two boxes.
- IDF1: tracking identity accuracy (higher is better).
- Latency: time from frame capture to alert/stream output.
- Event precision: fraction of alerts that are true events.
- Backpressure: queue limits that prevent pipeline overload.
- Frame skipping: process every k-th frame to reduce inference cost.
- Asynchronous processing: workers run in parallel for throughput.

## 8) Performance and Metrics (Estimated)
Note: these are design-derived estimates and must be validated with real benchmarks.

| Metric | Estimate | Why it matters |
| --- | --- | --- |
| End-to-end latency (k=3) | ~91 ms | Low latency improves response time |
| Throughput (k=3) | ~11 FPS | Maintains real-time feel on CPU |
| Event precision | ~0.87 | Fewer false alerts |

Why tracking improves accuracy
- Stable IDs reduce duplicate alerts and enable time-based behavior logic.

How the system measures it
- Stage latency is tracked per packet using timestamps.
- FPS is estimated from average inference time for operator feedback.
- Queue depth exposes backpressure and helps explain latency spikes.

## 9) Design Decisions (Critical WHYs)
- Rule-based behavior vs ML: explainable, no heavy training data, easier validation.
- CPU-first design: lightweight models + frame skipping keep it real-time without GPU.
- Asynchronous pipeline: avoids blocking and keeps stream responsive.
- Bounded queues: low latency and controlled memory use.
- Deduplication stack: prevents alert storms and reduces false positives.

## 10) Challenges and Solutions
- Performance bottlenecks: frame skipping, resolution caps, queue backpressure.
- Duplicate alerts: stability thresholds, cooldowns, dedup window.
- Tracking under occlusion: ByteTrack for stronger ID continuity.
- UI zone alignment: normalized zones against rendered video viewport.
- Upload deletion issues: stop pipeline and reset source before deletion.

## 11) API Surface (Selected)
Core control
- /health
- /camera/start, /camera/stop, /camera/status, /camera/stream
- /video/source, /video/demo/list, /video/upload

Alerts and analytics
- /alerts
- /analytics (alerts-over-time, distribution, summary, recent, threat)
- /system (status, metrics, alerts/stats, module enable/disable)

Reports and watchlist
- /reports (list, generate, download, scheduler status)
- /faces (register, list, delete)

Auth
- /auth/signup, /auth/login
- JWT-based bearer tokens; protected routes include analytics, reports, video source control, and uploads.

Why this grouping matters
- Control endpoints keep the pipeline start/stop and source switching separate from analytics.
- Analytics endpoints are read-heavy and optimized for aggregation.
- Reports are batch artifacts that can be generated on demand or on schedule.

## 12) Data Model (Database tables)
- alerts: event_type, zone, track_id, timestamp, snapshot_path, metadata
- zones: normalized rectangle, type, camera_id, created_at
- faces: name, embedding, created_at
- users: email, password_hash, created_at

## 13) Deployment and Runtime Notes
- Docker compose brings up frontend, backend, Postgres, and Redis.
- Backend falls back to SQLite if Postgres is unavailable.
- MJPEG streaming is used for live preview in the UI.
- Reporting generates JSON and CSV artifacts; optional SMTP delivery.

## 14) Limitations and Future Work
- CPU-only throughput limit under heavy loads.
- Design metrics are not yet empirically validated.
- Planned modules: abandoned object, speed anomaly, richer alert streaming.

## 15) Common Viva Questions (Short Answers)
Q: Why YOLOv8 over Faster R-CNN or SSD?
A: YOLOv8n is fastest on CPU; Faster R-CNN is too slow, SSD is weaker on small or occluded targets.

Q: Why ByteTrack over SORT or DeepSORT?
A: ByteTrack improves ID continuity without heavy re-ID compute.

Q: What is the core innovation?
A: A modular, CPU-first, asynchronous pipeline with explainable behavior rules and multi-layer alert dedup.

Q: How do you handle latency?
A: Frame skipping, bounded queues, resolution caps, parallel workers.

Q: Detection vs tracking?
A: Detection finds objects per frame; tracking links them across time for stable IDs and behavior reasoning.

Q: What are the limitations?
A: CPU-only throughput and some behavior modules planned but not fully implemented.

## 16) Short Explanation Scripts
30-second script
OVERWATCH is a real-time AI surveillance pipeline. It captures video, runs YOLOv8n detection, tracks people with ByteTrack, and applies rule-based logic for intrusion, loitering, crowd, and weapon events. Alerts are deduplicated, stored with snapshots, and shown on a React dashboard via MJPEG streaming. The system is optimized for CPU-only deployment with asynchronous workers and bounded queues.

1-minute script
OVERWATCH converts raw CCTV or RTSP video into actionable security alerts. Frames are captured and passed to YOLOv8n for detection, then ByteTrack stabilizes identities across frames. A behavior engine checks intrusion, loitering, crowd thresholds, and weapon detections with temporal stability and cooldowns. Alerts are queued to avoid blocking, persisted to PostgreSQL with snapshots, and summarized in analytics and reports. The system is designed for CPU-only environments using frame skipping, resolution caps, and asynchronous workers with bounded queues to keep latency low.

## 17) Keywords (1-line meanings)
- YOLOv8n: fast one-stage object detector for real-time inference.
- ByteTrack: tracker that improves ID continuity using low-confidence detections.
- IoU: overlap score between boxes used for accuracy and tracking association.
- IDF1: identity consistency metric for tracking quality.
- Backpressure: queue limits that prevent pipeline overload.
- Frame skipping: process every k-th frame to reduce compute load.
- MJPEG: stream of JPEG frames for live browser preview.
- Deduplication window: suppresses repeated alerts for the same event.
- Threat scoring: weighted signal sum yielding LOW to CRITICAL levels.
- Zone normalization: store zones in [0,1] coordinates relative to frame.

End of document
