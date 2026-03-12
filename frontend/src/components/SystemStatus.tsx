import { useSystemStatus, useSystemMetrics } from "../hooks/useSystemStatus";
import { Activity, Camera, Gauge, AlertTriangle, Layers } from "lucide-react";

export default function SystemStatus() {
  const { data: status } = useSystemStatus();
  const { data: metrics } = useSystemMetrics();

  const queueTotal = metrics?.queues
    ? Object.values(metrics.queues).reduce((a, b) => a + b, 0)
    : 0;

  const stats = [
    {
      label: "Camera",
      value: status?.camera_running ? "Online" : "Offline",
      icon: Camera,
      color: status?.camera_running ? "text-ow-accent" : "text-ow-alert-intrusion",
    },
    {
      label: "Pipeline FPS",
      value: status?.pipeline_fps?.toFixed(1) ?? "—",
      icon: Gauge,
      color: "text-ow-accent",
    },
    {
      label: "Alerts Total",
      value: status?.alerts_total?.toString() ?? "0",
      icon: AlertTriangle,
      color: "text-ow-alert-loitering",
    },
    {
      label: "Queue Depth",
      value: queueTotal.toString(),
      icon: Layers,
      color: "text-ow-alert-crowd",
    },
    {
      label: "Capture Items",
      value: metrics?.capture?.items_processed?.toString() ?? "—",
      icon: Activity,
      color: "text-ow-accent-dim",
    },
    {
      label: "Inference Avg",
      value: metrics?.inference?.processing_time_avg != null
        ? `${(Number(metrics.inference.processing_time_avg) * 1000).toFixed(0)}ms`
        : "—",
      icon: Activity,
      color: "text-ow-mist",
    },
  ];

  return (
    <div className="glass-panel rounded-2xl p-4 h-full">
      <h3 className="text-sm font-semibold text-ow-mist/70 uppercase tracking-wider mb-3">System</h3>
      <div className="space-y-2">
        {stats.map((s) => (
          <div
            key={s.label}
            className="flex items-center justify-between p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]"
          >
            <div className="flex items-center gap-3">
              <s.icon className={`w-4 h-4 ${s.color}`} />
              <span className="text-sm text-ow-mist/60">{s.label}</span>
            </div>
            <span className={`text-sm font-mono font-semibold ${s.color}`}>{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
