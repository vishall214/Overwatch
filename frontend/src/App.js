import React, { useState, useEffect, useCallback } from "react";
import "./App.css";
import CameraControls from "./components/CameraControls";
import VideoStream from "./components/VideoStream";
import StatusPanel from "./components/StatusPanel";

const API = "http://127.0.0.1:8000";

function App() {
  const [status, setStatus] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/camera/status`);
      if (res.ok) setStatus(await res.json());
    } catch {
      setStatus(null);
    }
  }, []);

  // Poll status every 2 seconds
  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, 2000);
    return () => clearInterval(id);
  }, [fetchStatus]);

  const isRunning = status?.is_running ?? false;

  return (
    <div className="dashboard">
      <h1>OVERWATCH</h1>
      <p className="subtitle">Surveillance Dashboard</p>
      <CameraControls isRunning={isRunning} onRefresh={fetchStatus} />
      <div className="main-row">
        <div className="videodisplay"><VideoStream isRunning={isRunning}/></div>
        <div className="statuspanel"><StatusPanel status={status}/></div>
      </div>
    </div>
  );
}

export default App;