import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getSourceInfo } from "../api/video";
import { useAlerts } from "../hooks/useAlerts";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { useCameraStatus } from "../hooks/useCameraStatus";
import { AlertTriangle, Camera, Gauge, Radar, Video } from "lucide-react";

type MonitorModule = "intrusion" | "loitering" | "crowd" | "weapon_detection";

const MODULE_LABELS: Record<MonitorModule, string> = {
  intrusion: "Intrusion",
  loitering: "Loitering",
  crowd: "Crowd",
  weapon_detection: "Weapons",
};

const SOURCE_LABELS: Record<string, string> = {
  camera: "Live",
  upload: "Upload",
  demo: "Demo",
};

export default function SystemStatus({ activeModule }: { activeModule?: MonitorModule }) {
  const { data: status } = useSystemStatus();
  const { data: cameraStatus } = useCameraStatus();
  const { data: sourceInfo } = useQuery({
    queryKey: ["sourceInfo"],
    queryFn: getSourceInfo,
    refetchInterval: 2000,
  });
  const { data: alertsData } = useAlerts(25);
  const cameraOnline = cameraStatus?.is_running ?? status?.camera_running ?? false;

  const resolvedModule = activeModule ?? (sourceInfo?.active_module as MonitorModule | undefined);
  const lastAlertTime = useMemo(() => {
    const alerts = alertsData?.alerts ?? [];
    if (!alerts.length) return "--";
    const latest = alerts.reduce((current, next) =>
      new Date(next.timestamp).getTime() > new Date(current.timestamp).getTime() ? next : current
    );
    return new Date(latest.timestamp).toLocaleTimeString();
  }, [alertsData?.alerts]);

  const stats = [
    {
      label: "Camera",
      value: cameraOnline ? "Online" : "Offline",
      icon: Camera,
      color: cameraOnline ? "text-accent" : "text-threat-critical",
    },
    {
      label: "FPS",
      value: status?.pipeline_fps?.toFixed(1) ?? "—",
      icon: Gauge,
      color: "text-accent",
    },
    {
      label: "Alerts",
      value: status?.alerts_total?.toString() ?? "0",
      icon: AlertTriangle,
      color: "text-threat-high",
    },
    {
      label: "Active Module",
      value: resolvedModule ? MODULE_LABELS[resolvedModule] : "None",
      icon: Radar,
      color: "text-textPrimary",
    },
    {
      label: "Source",
      value: sourceInfo?.source_type ? SOURCE_LABELS[sourceInfo.source_type] ?? sourceInfo.source_type : "Unknown",
      icon: Video,
      color: "text-textSecondary",
    },
    {
      label: "Last Alert",
      value: lastAlertTime,
      icon: AlertTriangle,
      color: "text-textSecondary",
    },
  ];

  return (
    <div className="glass glass-hover rounded-xl p-4 h-full">
      <h3 className="text-sm font-semibold text-textSecondary uppercase tracking-wider mb-3">System</h3>
      <div className="space-y-2">
        {stats.map((s) => (
          <div
            key={s.label}
            className="glass rounded-lg px-3 py-2 flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <s.icon className={`w-4 h-4 ${s.color}`} />
              <span className="text-sm text-textSecondary">{s.label}</span>
            </div>
            <span className={`text-sm font-mono font-semibold ${s.color}`}>{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
