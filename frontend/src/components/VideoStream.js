import React from "react";

const API = "http://127.0.0.1:8000";

export default function VideoStream({ isRunning }) {
  return (
    <div className="stream-section">
      <h2>Live Detection Stream</h2>
      <div className="stream-container">
        {isRunning ? (
          <img
            src={`${API}/camera/stream`}
            alt="OVERWATCH live feed"
          />
        ) : (
          <div className="stream-placeholder">
            Pipeline stopped — start camera to view feed
          </div>
        )}
      </div>
    </div>
  );
}
