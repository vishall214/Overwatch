import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useAlerts } from "../hooks/useAlerts";
import { API } from "../api/config";
import { AlertTriangle, ShieldAlert, Users, Eye } from "lucide-react";

const eventConfig: Record<string, { icon: typeof AlertTriangle; color: string }> = {
  intrusion: { icon: ShieldAlert, color: "text-ow-alert-intrusion" },
  loitering: { icon: Eye, color: "text-ow-alert-loitering" },
  crowd: { icon: Users, color: "text-ow-alert-crowd" },
};

export default function AlertsPanel() {
  const { data, isLoading } = useAlerts(20);
  const listRef = useRef<HTMLDivElement>(null);
  const prevCountRef = useRef(0);

  useEffect(() => {
    if (!data || !listRef.current) return;
    const newCount = data.alerts.length;
    if (newCount > prevCountRef.current) {
      const newCards = listRef.current.querySelectorAll(".alert-card");
      const toAnimate = Array.from(newCards).slice(0, newCount - prevCountRef.current);
      if (toAnimate.length > 0) {
        gsap.fromTo(
          toAnimate,
          { opacity: 0, x: -16, scale: 0.97 },
          { opacity: 1, x: 0, scale: 1, duration: 0.35, stagger: 0.04, ease: "power2.out" }
        );
      }
    }
    prevCountRef.current = newCount;
  }, [data]);

  if (isLoading) {
    return (
      <GlassCard title="Alerts">
        <div className="flex items-center justify-center h-32 text-ow-mist/40 text-sm">Loading alerts...</div>
      </GlassCard>
    );
  }

  const alerts = data?.alerts ?? [];

  return (
    <GlassCard title="Alerts" badge={alerts.length}>
      <div ref={listRef} className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
        {alerts.length === 0 ? (
          <div className="text-center text-ow-mist/30 text-sm py-6">No alerts detected</div>
        ) : (
          alerts.map((alert) => {
            const cfg = eventConfig[alert.event_type] ?? { icon: AlertTriangle, color: "text-ow-accent" };
            const Icon = cfg.icon;
            const snapshotFile = alert.snapshot_path?.split("/").pop() ?? "";
            return (
              <div
                key={alert.id}
                className="alert-card flex items-start gap-3 p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.05)]
                           hover:bg-ow-teal/15 hover:border-ow-accent/15 transition-all duration-200 cursor-default group"
              >
                {snapshotFile && (
                  <img
                    src={API.snapshots(snapshotFile)}
                    alt="snapshot"
                    className="w-14 h-14 rounded-lg object-cover flex-shrink-0 border border-[rgba(255,255,255,0.08)]"
                    loading="lazy"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Icon className={`w-3.5 h-3.5 ${cfg.color}`} />
                    <span className="text-sm font-medium capitalize text-ow-light/90">{alert.event_type}</span>
                  </div>
                  <div className="text-xs text-ow-mist/50 mt-0.5">
                    Zone: {alert.zone || "—"} &middot; Track {alert.track_id ?? "—"}
                  </div>
                  <div className="text-[10px] text-ow-mist/25 mt-1 font-mono">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </GlassCard>
  );
}

function GlassCard({ title, badge, children }: { title: string; badge?: number; children: React.ReactNode }) {
  return (
    <div className="glass-panel rounded-2xl p-4 h-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-ow-mist/70 uppercase tracking-wider">{title}</h3>
        {badge !== undefined && (
          <span className="px-2 py-0.5 rounded-full bg-ow-accent/10 text-ow-accent text-xs font-mono">
            {badge}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}
