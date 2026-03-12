import React from "react";

export default function StatusPanel({ status }) {
  if (!status) {
    return (
      <div className="status-section">
        <h2>Pipeline Status</h2>
        <p className="status-offline">Waiting for backend…</p>
      </div>
    );
  }

  const running = status.is_running;
  const inf = status.inference_worker || {};
  const cap = status.capture_worker || {};
  const q = status.queues || {};

  return (
    <div className="status-section">
      <h2>Pipeline Status</h2>
      <div className="status-grid">
        <Row label="running" value={String(running)} highlight={running} />
        <Row label="frames_captured" value={cap.frames_captured ?? "—"} />
        <Row label="frames_inferred" value={inf.frames_processed ?? "—"} />
        <Row label="avg_inference_ms" value={inf.avg_inference_ms ?? "—"} />
        <Row label="frame_queue" value={q.frame_queue ?? "—"} />
        <Row label="detection_queue" value={q.detection_queue ?? "—"} />
        <Row label="stream_queue" value={q.stream_queue ?? "—"} />
      </div>
    </div>
  );
}

function Row({ label, value, highlight }) {
  let cls = "value";
  if (highlight === true) cls += " running";
  if (highlight === false) cls += " stopped";

  return (
    <div className="row">
      <span className="label">{label}</span>
      <span className={cls}>{value}</span>
    </div>
  );
}
