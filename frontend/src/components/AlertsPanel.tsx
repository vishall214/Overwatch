import { useEffect, useRef, useState, type ReactNode } from "react";
import gsap from "gsap";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Crosshair, Eye, ShieldAlert, UserCheck, Users } from "lucide-react";
import { useAlerts } from "../hooks/useAlerts";
import { extractSnapshotFilename, resolveSnapshotSrc } from "../utils/snapshot";
import { resolveThreatInfo } from "../utils/threat";
import { formatEventLabel, normalizeEventType } from "../utils/normalization";
import { threatBadgeBgClasses, threatColorClasses } from "../theme/threat";

const eventIcons: Record<string, typeof AlertTriangle> = {
  intrusion: ShieldAlert,
  loitering: Eye,
  crowd: Users,
  weapon_in_zone: Crosshair,
  weapon_detected: Crosshair,
  face_match: UserCheck,
};

export const severityStyles = {
  CRITICAL: "border-l-4 border-red-500 bg-red-500/5",
  HIGH: "border-l-4 border-orange-500 bg-orange-500/5",
  MEDIUM: "border-l-4 border-yellow-500 bg-yellow-500/5",
  LOW: "border-l-4 border-teal-400 bg-teal-400/5",
} as const;

const objectMetadataKeys = [
  "object",
  "object_type",
  "object_label",
  "detected_object",
  "class_name",
  "label",
  "weapon_type",
] as const;

function getMetadataText(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return null;
}

function extractObjectLabel(metadata: Record<string, unknown>): string | null {
  for (const key of objectMetadataKeys) {
    const text = getMetadataText(metadata[key]);
    if (text) return text;
  }
  return null;
}

export type AlertItem = {
  id: number | string;
  event_type: string;
  timestamp: string;
  zone?: string;
  track_id?: number | null;
  metadata?: Record<string, unknown>;
  snapshot_filename?: string;
  snapshot_path?: string;
  snapshot_url?: string;
};

export type AlertCardModel = {
  id: number | string;
  icon: typeof AlertTriangle;
  eventType: string;
  title: string;
  severity: string;
  zone: string;
  objectLabel: string | null;
  contextText: string;
  timeText: string;
  threatScore: number;
  snapshotSrc: string | null;
  metadata: Record<string, unknown>;
};

export function buildAlertCardModel(alert: AlertItem): AlertCardModel {
  const normalizedType = normalizeEventType(alert.event_type);
  const Icon = eventIcons[normalizedType] ?? AlertTriangle;
  const metadata = (alert.metadata as Record<string, unknown>) ?? {};
  const snapshotFile = extractSnapshotFilename(alert as Record<string, unknown>);
  const snapshotSrc = snapshotFile ? resolveSnapshotSrc(alert as Record<string, unknown>) : null;
  const threat = resolveThreatInfo(alert as Record<string, unknown>);
  const zone = alert.zone?.trim() || "--";
  const objectLabel = extractObjectLabel(metadata);
  const contextText = [zone !== "--" ? zone : null, objectLabel].filter(Boolean).join(" / ") || "Context unavailable";

  return {
    id: alert.id,
    icon: Icon,
    eventType: normalizedType,
    title: formatEventLabel(normalizedType),
    severity: threat.level,
    zone,
    objectLabel,
    contextText,
    timeText: new Date(alert.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }),
    threatScore: threat.score,
    snapshotSrc,
    metadata,
  };
}

function SnapshotThumb({ src }: { src: string | null }) {
  const [broken, setBroken] = useState(false);
  if (!src || broken) {
    return (
      <div className="w-14 h-14 rounded-lg bg-surface border border-border flex items-center justify-center flex-shrink-0">
        <AlertTriangle className="w-4 h-4 text-textMuted" />
      </div>
    );
  }

  return (
    <img
      src={src}
      alt="snapshot"
      className="w-14 h-14 rounded-lg object-cover flex-shrink-0 border border-border"
      loading="lazy"
      onError={() => setBroken(true)}
    />
  );
}

export function AlertCard({
  alert,
  compact = false,
  selected = false,
  showSnapshot = true,
  onClick,
}: {
  alert: AlertItem;
  compact?: boolean;
  selected?: boolean;
  showSnapshot?: boolean;
  onClick?: (alertId: number | string) => void;
}) {
  const model = buildAlertCardModel(alert);
  const severityClass = severityStyles[model.severity as keyof typeof severityStyles] ?? severityStyles.LOW;
  const levelClass = threatColorClasses[model.severity as keyof typeof threatColorClasses];
  const levelBgClass = threatBadgeBgClasses[model.severity as keyof typeof threatBadgeBgClasses];

  return (
    <button
      type="button"
      onClick={() => onClick?.(model.id)}
      className={`alert-card w-full text-left rounded-xl p-3 border border-border transition-all hover:bg-card flex items-start gap-3 ${severityClass} ${
        selected ? "ring-2 ring-teal-400/60 scale-[1.01]" : ""
      }`}
    >
      {showSnapshot ? (
        <SnapshotThumb src={model.snapshotSrc} />
      ) : (
        <div className="w-10 h-10 rounded-lg bg-surface border border-border flex items-center justify-center flex-shrink-0">
          <model.icon className="w-4 h-4 text-textSecondary" />
        </div>
      )}

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-textPrimary truncate">{model.title}</span>
          <span
            className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold uppercase border whitespace-nowrap ${levelClass} ${levelBgClass}`}
          >
            {model.severity}
          </span>
        </div>
        <p className="text-xs text-textSecondary mt-1">{model.timeText}</p>
        <p className={`text-xs text-textMuted mt-1 ${compact ? "truncate" : ""}`}>{model.contextText}</p>
        <p className="text-xs text-textMuted mt-1">Threat {model.threatScore}</p>
      </div>
    </button>
  );
}

export default function AlertsPanel({ compact = false }: { compact?: boolean }) {
  const navigate = useNavigate();
  const { data, isLoading } = useAlerts(20);
  const listRef = useRef<HTMLDivElement>(null);
  const prevCountRef = useRef(0);
  const maxVisibleAlerts = compact ? 6 : 8;

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
      <PanelCard title="Alerts" compact={compact}>
        <div className="flex items-center justify-center h-32 text-sm text-textSecondary">Loading alerts...</div>
      </PanelCard>
    );
  }

  const sorted = [...(data?.alerts ?? [])]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, maxVisibleAlerts);

  return (
    <PanelCard title="Alerts" badge={sorted.length} compact={compact}>
      <div ref={listRef} className={`space-y-2 overflow-y-auto pr-1 ${compact ? "flex-1 min-h-0" : "max-h-[320px]"}`}>
        {sorted.length === 0 ? (
          <div className="text-center text-sm text-textSecondary py-6">No alerts detected</div>
        ) : (
          sorted.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              compact={compact}
              showSnapshot={!compact}
              onClick={(alertId) => navigate(`/alerts?selected=${alertId}`)}
            />
          ))
        )}
      </div>
    </PanelCard>
  );
}

function PanelCard({
  title,
  badge,
  children,
  compact = false,
}: {
  title: string;
  badge?: number;
  children: ReactNode;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "h-full flex flex-col" : "glass rounded-xl p-4 h-full flex flex-col"}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-textPrimary">{title}</h3>
        {badge !== undefined ? <span className="text-xs text-textSecondary">{badge}</span> : null}
      </div>
      {children}
    </div>
  );
}
