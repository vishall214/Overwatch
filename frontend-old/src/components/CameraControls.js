import React, { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function CameraControls({ isRunning, onRefresh }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function startCamera() {
    setBusy(true);
    setMessage("Starting pipeline…");
    try {
      const res = await fetch(`${API}/camera/start`, { method: "POST" });
      if (res.ok) {
        setMessage("Pipeline started");
      } else {
        const body = await res.json().catch(() => ({}));
        setMessage(body.detail || "Failed to start");
      }
    } catch {
      setMessage("Backend unreachable");
    }
    setBusy(false);
    onRefresh();
  }

  async function stopCamera() {
    setBusy(true);
    setMessage("Stopping pipeline…");
    try {
      const res = await fetch(`${API}/camera/stop`, { method: "POST" });
      if (res.ok) {
        setMessage("Pipeline stopped");
      } else {
        const body = await res.json().catch(() => ({}));
        setMessage(body.detail || "Failed to stop");
      }
    } catch {
      setMessage("Backend unreachable");
    }
    setBusy(false);
    onRefresh();
  }

  return (
    <div className="controls">
      <button
        className="btn-start"
        onClick={startCamera}
        disabled={busy || isRunning}
      >
        Start Camera
      </button>
      <button
        className="btn-stop"
        onClick={stopCamera}
        disabled={busy || !isRunning}
      >
        Stop Camera
      </button>
      <div className="message">{message}</div>
    </div>
  );
}
