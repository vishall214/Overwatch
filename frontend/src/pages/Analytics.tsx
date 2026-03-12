import { useState, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { useAlertStats } from "../hooks/useAlerts";
import { useSystemMetrics } from "../hooks/useSystemStatus";
import { Navigate } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadialBarChart,
  RadialBar,
} from "recharts";
import { Upload, CheckCircle, Loader2, BarChart3 } from "lucide-react";

const COLORS = ["#2BD4A8", "#FF4D4D", "#FF9F40", "#3BA8FF", "#1BC47F"];

export default function Analytics() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <AnalyticsContent />;
}

function AnalyticsContent() {
  const { data: alertStats } = useAlertStats();
  const { data: metrics } = useSystemMetrics();

  // Alert distribution data
  const distData = alertStats
    ? [
        { name: "Intrusion", value: alertStats.intrusion },
        { name: "Loitering", value: alertStats.loitering },
        { name: "Crowd", value: alertStats.crowd },
        { name: "Face Match", value: alertStats.face_match },
      ].filter((d) => d.value > 0)
    : [];

  // Pipeline performance data
  const pipelineData = metrics
    ? Object.entries(metrics)
        .filter(([k]) => k !== "queues")
        .map(([name, stage]) => ({
          name: name.charAt(0).toUpperCase() + name.slice(1),
          processed: (stage as Record<string, unknown>).items_processed as number ?? 0,
          avgTime: Number(((stage as Record<string, unknown>).processing_time_avg as number ?? 0).toFixed(2)),
        }))
    : [];

  // Queue data
  const queueData = metrics?.queues
    ? Object.entries(metrics.queues).map(([name, size]) => ({
        name,
        value: size,
        fill: COLORS[Math.abs(name.charCodeAt(0)) % COLORS.length],
      }))
    : [];

  return (
    <div className="space-y-5">
      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Alerts", value: alertStats?.total_alerts ?? 0, color: "text-ow-accent" },
          { label: "Intrusion", value: alertStats?.intrusion ?? 0, color: "text-ow-alert-intrusion" },
          { label: "Loitering", value: alertStats?.loitering ?? 0, color: "text-ow-alert-loitering" },
          { label: "Crowd", value: alertStats?.crowd ?? 0, color: "text-ow-alert-crowd" },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl glass-panel p-5">
            <div className="text-xs text-ow-mist/35 uppercase tracking-wider mb-2">{s.label}</div>
            <div className={`text-3xl font-bold font-mono ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Alert distribution */}
        <div className="rounded-2xl glass-panel p-5">
          <h3 className="text-sm font-semibold text-ow-mist/70 uppercase tracking-wider mb-4">Alert Distribution</h3>
          {distData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={distData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  dataKey="value"
                  stroke="none"
                >
                  {distData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "rgba(6,30,41,0.95)",
                    border: "1px solid rgba(43,212,168,0.15)",
                    borderRadius: "12px",
                    color: "#F3F4F4",
                    fontSize: "12px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[250px] text-ow-mist/25 text-sm">No data</div>
          )}
          <div className="flex flex-wrap gap-4 mt-2 justify-center">
            {distData.map((d, i) => (
              <div key={d.name} className="flex items-center gap-2 text-xs">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                <span className="text-ow-mist/50">{d.name}: {d.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline performance bar chart */}
        <div className="rounded-2xl glass-panel p-5">
          <h3 className="text-sm font-semibold text-ow-mist/70 uppercase tracking-wider mb-4">Pipeline Performance</h3>
          {pipelineData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={pipelineData}>
                <XAxis dataKey="name" stroke="#ffffff30" fontSize={11} tickLine={false} />
                <YAxis stroke="#ffffff30" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(6,30,41,0.95)",
                    border: "1px solid rgba(43,212,168,0.15)",
                    borderRadius: "12px",
                    color: "#F3F4F4",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="processed" fill="#2BD4A8" radius={[6, 6, 0, 0]} name="Items Processed" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[280px] text-ow-mist/25 text-sm">No metrics</div>
          )}
        </div>
      </div>

      {/* Queue status */}
      <div className="rounded-2xl glass-panel p-5">
        <h3 className="text-sm font-semibold text-ow-mist/70 uppercase tracking-wider mb-4">Queue Status</h3>
        {queueData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <RadialBarChart cx="50%" cy="50%" innerRadius="20%" outerRadius="90%" data={queueData}>
              <RadialBar dataKey="value" cornerRadius={8} />
              <Tooltip
                contentStyle={{
                  background: "rgba(6,30,41,0.95)",
                  border: "1px solid rgba(43,212,168,0.15)",
                  borderRadius: "12px",
                  color: "#F3F4F4",
                  fontSize: "12px",
                }}
              />
            </RadialBarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-[200px] text-ow-mist/25 text-sm">No queue data</div>
        )}
      </div>

      {/* Video Upload Section */}
      <VideoUpload />
    </div>
  );
}

function VideoUpload() {
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [result, setResult] = useState<string>("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    setStatus("uploading");
    setResult("");

    try {
      const formData = new FormData();
      formData.append("video", file);

      const res = await fetch("http://127.0.0.1:8000/upload-video", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
      setStatus("done");
    } catch {
      setResult("Upload failed or endpoint not available.");
      setStatus("error");
    }
  };

  return (
    <div className="rounded-2xl glass-panel p-6">
      <div className="flex items-center gap-3 mb-4">
        <BarChart3 className="w-5 h-5 text-ow-accent" />
        <h3 className="text-sm font-semibold text-ow-mist/70 uppercase tracking-wider">Video Upload Demo</h3>
      </div>
      <div className="flex items-center gap-4">
        <input
          ref={fileRef}
          type="file"
          accept="video/*"
          className="text-sm text-ow-mist/50 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0
                     file:text-sm file:font-medium file:bg-ow-accent/10 file:text-ow-accent
                     hover:file:bg-ow-accent/20 file:cursor-pointer file:transition-colors"
        />
        <button
          onClick={handleUpload}
          disabled={status === "uploading"}
          className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-ow-accent to-ow-accent-dim
                     text-sm font-semibold text-ow-bg hover:shadow-glow-hover transition-all
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {status === "uploading" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : status === "done" ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <Upload className="w-4 h-4" />
          )}
          {status === "uploading" ? "Processing..." : "Upload Video"}
        </button>
      </div>
      {result && (
        <pre className="mt-4 p-4 rounded-xl bg-ow-bg/50 border border-[rgba(255,255,255,0.04)] text-xs text-ow-mist/50 font-mono overflow-x-auto">
          {result}
        </pre>
      )}
    </div>
  );
}
