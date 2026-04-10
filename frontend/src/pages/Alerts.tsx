import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, ArrowDownUp, ChevronDown, ChevronRight, Filter, Search, X } from "lucide-react";
import { AlertCard, buildAlertCardModel, type AlertCardModel, type AlertItem } from "../components/AlertsPanel";
import { useAlerts } from "../hooks/useAlerts";
import { formatEventLabel, normalizeEventType } from "../utils/normalization";
import { threatBadgeBgClasses, threatColorClasses } from "../theme/threat";

type SortField = "timestamp" | "event_type" | "zone" | "threat_score";
type SortDir = "asc" | "desc";
type RangeFilter = "all" | "1h" | "6h" | "24h";
type FilterType = "all" | "intrusion" | "loitering" | "crowd" | "weapon_detected" | "weapon_in_zone";

type AlertChain = {
  id: string;
  alerts: AlertItem[];
  eventType: string;
  startMs: number;
  endMs: number;
  dominantType: string;
  dominantModel: AlertCardModel;
};

type TimelineNode = {
  key: string;
  label: string;
  detail: string;
};

const FILTER_TYPES: readonly FilterType[] = Array.from(
  new Set<FilterType>(["all", "intrusion", "loitering", "crowd", "weapon_detected", "weapon_in_zone"])
);
const SORT_FIELDS = ["timestamp", "event_type", "zone", "threat_score"] as const;
const RANGE_FILTERS = ["all", "1h", "6h", "24h"] as const;

const CHAIN_WINDOW_MS = 30_000;
const NEARBY_WINDOW_MS = 20_000;
const HOUR_MS = 60 * 60 * 1000;

const persistenceMetadataKeys = ["duration_s", "duration_seconds", "dwell_seconds", "loitering_seconds", "persistence_seconds"] as const;
const objectTypeMetadataKeys = ["object_type", "class_name", "detected_object", "object", "label", "weapon_type"] as const;

function normalizeFilterType(value: string | null): FilterType {
  if (!value) return "all";

  const normalized = normalizeEventType(value);
  if (FILTER_TYPES.includes(normalized as FilterType)) return normalized as FilterType;
  if (FILTER_TYPES.includes(value as FilterType)) return value as FilterType;
  return "all";
}

function toFilterLabel(value: FilterType) {
  if (value === "all") return "All";
  return formatEventLabel(value);
}

function parseNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function asText(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return null;
}

function getPersistenceSeconds(metadata: Record<string, unknown>): number | null {
  for (const key of persistenceMetadataKeys) {
    const value = parseNumber(metadata[key]);
    if (value !== null) return value;
  }
  return null;
}

function getObjectTypeKey(alert: AlertItem, model: AlertCardModel): string | null {
  const metadata = (alert.metadata as Record<string, unknown>) ?? {};

  for (const key of objectTypeMetadataKeys) {
    const text = asText(metadata[key]);
    if (text) return text.toLowerCase();
  }

  if (model.objectLabel) return model.objectLabel.toLowerCase();
  return null;
}

function getRangeWindowMs(range: RangeFilter): number | null {
  if (range === "1h") return 1 * HOUR_MS;
  if (range === "6h") return 6 * HOUR_MS;
  if (range === "24h") return 24 * HOUR_MS;
  return null;
}

function formatClock(valueMs: number) {
  return new Date(valueMs).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatChainRange(startMs: number, endMs: number) {
  return `${formatClock(startMs)} -> ${formatClock(endMs)}`;
}

function deriveWhyThisMatters(alert: AlertItem, model: AlertCardModel): string[] {
  const eventType = normalizeEventType(alert.event_type);
  const metadata = (alert.metadata as Record<string, unknown>) ?? {};
  const reasons: string[] = [];

  if (eventType === "weapon_in_zone") {
    reasons.push("Weapon detected inside restricted zone.");
  } else if (eventType === "intrusion") {
    reasons.push("Unauthorized entry detected in monitored zone.");
  } else if (eventType === "crowd") {
    reasons.push("Crowd density exceeded configured threshold in monitored area.");
  } else if (eventType === "loitering") {
    reasons.push("Object remained beyond allowed duration.");
  } else if (eventType === "weapon_detected") {
    reasons.push("Weapon detected in monitored field requiring verification.");
  } else {
    reasons.push(`${formatEventLabel(eventType)} requires focused operator review.`);
  }

  const persistence = getPersistenceSeconds(metadata);
  if (persistence !== null && persistence >= 5) {
    reasons.push(`Activity persisted for ${Math.round(persistence)} seconds.`);
  } else if (model.threatScore >= 80) {
    reasons.push(`Threat score ${model.threatScore} indicates elevated operational risk.`);
  }

  return reasons.slice(0, 2);
}

function hasEscalationFlag(metadata: Record<string, unknown>) {
  const candidateValues = [metadata.escalated, metadata.is_escalated, metadata.escalation];

  return candidateValues.some((value) => {
    if (typeof value === "boolean") return value;
    if (typeof value === "string") {
      const lowered = value.toLowerCase();
      return lowered === "true" || lowered === "yes" || lowered === "escalated";
    }
    return false;
  });
}

function buildEventTimeline(alert: AlertItem, model: AlertCardModel, nearbyEventsCount: number): TimelineNode[] {
  const metadata = (alert.metadata as Record<string, unknown>) ?? {};
  const persistence = getPersistenceSeconds(metadata);
  const detectedAt = new Date(alert.timestamp);
  const persisted = (persistence ?? 0) >= 5 || nearbyEventsCount > 0;
  const escalated = hasEscalationFlag(metadata) || (persisted && (model.severity === "HIGH" || model.severity === "CRITICAL"));

  const nodes: TimelineNode[] = [
    {
      key: "detected",
      label: "Detected",
      detail: detectedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    },
  ];

  if (persisted) {
    nodes.push({
      key: "persisted",
      label: "Persisted",
      detail: persistence !== null ? `${Math.round(persistence)}s observed` : "Follow-up events detected",
    });
  }

  if (escalated) {
    nodes.push({
      key: "escalated",
      label: "Escalated",
      detail: `Escalated to ${model.severity}`,
    });
  }

  return nodes;
}

function suggestAction(severity: string): "Monitor" | "Escalate" | "Ignore" {
  if (severity === "CRITICAL" || severity === "HIGH") return "Escalate";
  if (severity === "MEDIUM") return "Monitor";
  return "Ignore";
}

function buildAlertChains(alerts: AlertItem[], modelMap: Map<string, AlertCardModel>): AlertChain[] {
  const chronological = [...alerts].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  const groups: Array<{
    alerts: AlertItem[];
    eventType: string;
    startMs: number;
    endMs: number;
    zones: Set<string>;
    objectTypes: Set<string>;
  }> = [];

  chronological.forEach((alert) => {
    const model = modelMap.get(String(alert.id)) ?? buildAlertCardModel(alert);
    const eventType = normalizeEventType(alert.event_type);
    const timestampMs = new Date(alert.timestamp).getTime();
    const zoneKey = model.zone !== "--" ? model.zone.toLowerCase() : null;
    const objectTypeKey = getObjectTypeKey(alert, model);

    let targetIndex = -1;

    for (let index = groups.length - 1; index >= 0; index -= 1) {
      const candidate = groups[index];
      if (timestampMs - candidate.endMs > CHAIN_WINDOW_MS) break;

      const zoneMatch = zoneKey ? candidate.zones.has(zoneKey) : false;
      const objectMatch = objectTypeKey ? candidate.objectTypes.has(objectTypeKey) : false;
      const eventTypeMatch = candidate.eventType === eventType;

      if (eventTypeMatch && (zoneMatch || objectMatch)) {
        targetIndex = index;
        break;
      }
    }

    if (targetIndex === -1) {
      groups.push({
        alerts: [alert],
        eventType,
        startMs: timestampMs,
        endMs: timestampMs,
        zones: new Set(zoneKey ? [zoneKey] : []),
        objectTypes: new Set(objectTypeKey ? [objectTypeKey] : []),
      });
      return;
    }

    const target = groups[targetIndex];
    target.alerts.push(alert);
    target.endMs = timestampMs;
    if (zoneKey) target.zones.add(zoneKey);
    if (objectTypeKey) target.objectTypes.add(objectTypeKey);
  });

  return groups.map((group, index) => {
    const typeCounts = group.alerts.reduce(
      (acc, alert) => {
        const normalizedType = normalizeEventType(alert.event_type);
        acc[normalizedType] = (acc[normalizedType] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    let dominantType = "unknown";
    let maxCount = -1;
    Object.entries(typeCounts).forEach(([type, count]) => {
      if (count > maxCount) {
        dominantType = type;
        maxCount = count;
      }
    });

    const dominantAlert = group.alerts.find((alert) => normalizeEventType(alert.event_type) === dominantType) ?? group.alerts[0];
    const dominantModel = modelMap.get(String(dominantAlert.id)) ?? buildAlertCardModel(dominantAlert);

    return {
      id: `chain-${group.startMs}-${group.endMs}-${index}`,
      alerts: [...group.alerts].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
      eventType: group.eventType,
      startMs: group.startMs,
      endMs: group.endMs,
      dominantType,
      dominantModel,
    };
  });
}

function sortChains(
  chains: AlertChain[],
  sortField: SortField,
  sortDir: SortDir,
  modelMap: Map<string, AlertCardModel>
): AlertChain[] {
  return [...chains].sort((a, b) => {
    let cmp = 0;

    if (sortField === "timestamp") {
      cmp = a.endMs - b.endMs;
    } else if (sortField === "event_type") {
      cmp = a.dominantType.localeCompare(b.dominantType);
    } else if (sortField === "zone") {
      cmp = a.dominantModel.zone.localeCompare(b.dominantModel.zone);
    } else {
      const aThreat = Math.max(
        ...a.alerts.map((alert) => (modelMap.get(String(alert.id)) ?? buildAlertCardModel(alert)).threatScore)
      );
      const bThreat = Math.max(
        ...b.alerts.map((alert) => (modelMap.get(String(alert.id)) ?? buildAlertCardModel(alert)).threatScore)
      );
      cmp = aThreat - bThreat;
    }

    return sortDir === "asc" ? cmp : -cmp;
  });
}

function SnapshotInvestigation({
  src,
  eventTitle,
  severity,
  timestamp,
}: {
  src: string | null;
  eventTitle: string;
  severity: string;
  timestamp: string;
}) {
  const [broken, setBroken] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    setBroken(false);
    setIsModalOpen(false);
  }, [src]);

  const canRenderImage = Boolean(src) && !broken;
  const timeText = new Date(timestamp).toLocaleString();
  const severityOverlayClasses = {
    CRITICAL: "bg-red-600/95 border-red-300 text-white shadow-lg shadow-red-900/60",
    HIGH: "bg-orange-500/95 border-orange-300 text-white shadow-lg shadow-orange-900/50",
    MEDIUM: "bg-yellow-500/95 border-yellow-300 text-black shadow-lg shadow-yellow-900/40",
    LOW: "bg-teal-500/95 border-teal-300 text-white shadow-lg shadow-teal-900/40",
  } as const;
  const severityOverlayClass =
    severityOverlayClasses[severity as keyof typeof severityOverlayClasses] ?? severityOverlayClasses.LOW;

  const renderFrame = (modal = false) => (
    <div
      className={`relative w-full rounded-xl border border-border overflow-hidden bg-surface transition-all duration-200 ${
        modal ? "max-h-[80vh]" : "aspect-video"
      } ${canRenderImage ? "hover:scale-[1.01]" : ""}`}
    >
      {canRenderImage ? (
        <img
          src={src ?? ""}
          alt="Alert snapshot"
          className={`w-full h-full transition-transform duration-200 ${modal ? "object-contain" : "object-cover hover:scale-[1.05]"}`}
          onError={() => setBroken(true)}
        />
      ) : (
        <div className="w-full h-full min-h-[220px] flex items-center justify-center">
          <p className="text-sm text-textSecondary">Snapshot unavailable</p>
        </div>
      )}

      <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-black/80 border border-white/20 text-xs font-semibold text-white">
        {eventTitle}
      </div>

      <div className={`absolute top-2 right-2 px-2.5 py-0.5 rounded-md text-xs font-bold border uppercase ${severityOverlayClass}`}>
        {severity}
      </div>

      <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-md bg-black/80 border border-white/20 text-xs text-white/90">
        {timeText}
      </div>
    </div>
  );

  return (
    <>
      <button
        type="button"
        onClick={() => {
          if (canRenderImage) setIsModalOpen(true);
        }}
        className="w-full text-left"
      >
        {renderFrame(false)}
      </button>

      {isModalOpen && canRenderImage ? (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => setIsModalOpen(false)}>
          <div className="relative w-full max-w-6xl" onClick={(event) => event.stopPropagation()}>
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="absolute -top-10 right-0 px-3 py-1.5 rounded-lg bg-surface border border-border text-textPrimary"
            >
              Close
            </button>
            {renderFrame(true)}
          </div>
        </div>
      ) : null}
    </>
  );
}

export default function Alerts() {
  const { data, isLoading } = useAlerts(200);
  const [searchParams, setSearchParams] = useSearchParams();

  const requestedType = searchParams.get("type");
  const requestedSort = searchParams.get("sort");
  const requestedSearch = searchParams.get("search") ?? "";
  const requestedRange = searchParams.get("range");

  const initialType = normalizeFilterType(requestedType);
  const initialSort =
    requestedSort && SORT_FIELDS.includes(requestedSort as (typeof SORT_FIELDS)[number])
      ? (requestedSort as SortField)
      : "timestamp";
  const initialRange =
    requestedRange && RANGE_FILTERS.includes(requestedRange as (typeof RANGE_FILTERS)[number])
      ? (requestedRange as RangeFilter)
      : "all";

  const [typeFilter, setTypeFilter] = useState<FilterType>(initialType);
  const [searchQuery, setSearchQuery] = useState(requestedSearch);
  const [sortField, setSortField] = useState<SortField>(initialSort);
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [rangeFilter, setRangeFilter] = useState<RangeFilter>(initialRange);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(searchParams.get("selected"));
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [inspectorVisible, setInspectorVisible] = useState(true);

  useEffect(() => {
    if (!selectedAlertId) {
      setInspectorVisible(true);
      return;
    }

    setInspectorVisible(false);
    const timer = window.setTimeout(() => setInspectorVisible(true), 40);
    return () => window.clearTimeout(timer);
  }, [selectedAlertId]);

  useEffect(() => {
    const nextType = searchParams.get("type");
    setTypeFilter(normalizeFilterType(nextType));

    const nextSort = searchParams.get("sort");
    if (nextSort && SORT_FIELDS.includes(nextSort as (typeof SORT_FIELDS)[number])) {
      setSortField(nextSort as SortField);
    }

    const nextSearch = searchParams.get("search") ?? "";
    setSearchQuery(nextSearch);

    const nextRange = searchParams.get("range");
    setRangeFilter(
      nextRange && RANGE_FILTERS.includes(nextRange as (typeof RANGE_FILTERS)[number])
        ? (nextRange as RangeFilter)
        : "all"
    );

    setSelectedAlertId(searchParams.get("selected"));
  }, [searchParams]);

  const alerts: AlertItem[] = (data?.alerts ?? []).map((alert) => ({
    id: alert.id,
    event_type: alert.event_type,
    timestamp: alert.timestamp,
    zone: alert.zone,
    track_id: alert.track_id,
    metadata: (alert.metadata as Record<string, unknown> | undefined) ?? {},
    snapshot_filename: alert.snapshot_filename,
    snapshot_path: alert.snapshot_path,
    snapshot_url: alert.snapshot_url,
  }));

  const modelMap = useMemo(() => {
    return new Map(alerts.map((alert) => [String(alert.id), buildAlertCardModel(alert)]));
  }, [alerts]);

  const rangeFilteredAlerts = useMemo(() => {
    const windowMs = getRangeWindowMs(rangeFilter);
    if (!windowMs) return alerts;

    const threshold = Date.now() - windowMs;
    return alerts.filter((alert) => new Date(alert.timestamp).getTime() >= threshold);
  }, [alerts, rangeFilter]);

  const filteredAlerts = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return rangeFilteredAlerts
      .filter((alert) => typeFilter === "all" || normalizeEventType(alert.event_type) === typeFilter)
      .filter((alert) => {
        if (!query) return true;
        const model = modelMap.get(String(alert.id)) ?? buildAlertCardModel(alert);
        const text = [model.title, model.zone, model.objectLabel ?? "", model.contextText].join(" ").toLowerCase();
        return text.includes(query);
      });
  }, [modelMap, rangeFilteredAlerts, searchQuery, typeFilter]);

  const alertChains = useMemo(() => buildAlertChains(filteredAlerts, modelMap), [filteredAlerts, modelMap]);

  const sortedChains = useMemo(
    () => sortChains(alertChains, sortField, sortDir, modelMap),
    [alertChains, modelMap, sortDir, sortField]
  );

  useEffect(() => {
    setExpandedGroups((previous) => {
      const next: Record<string, boolean> = {};
      sortedChains.forEach((chain) => {
        next[chain.id] = previous[chain.id] ?? chain.alerts.length <= 2;
      });
      return next;
    });
  }, [sortedChains]);

  const selectedAlert = useMemo(() => {
    if (!selectedAlertId) return null;
    return filteredAlerts.find((alert) => String(alert.id) === selectedAlertId) ?? null;
  }, [filteredAlerts, selectedAlertId]);

  const selectedModel = useMemo(() => {
    if (!selectedAlert) return null;
    return modelMap.get(String(selectedAlert.id)) ?? buildAlertCardModel(selectedAlert);
  }, [modelMap, selectedAlert]);

  const nearbyEvents = useMemo(() => {
    if (!selectedAlert) return [];

    const selectedTime = new Date(selectedAlert.timestamp).getTime();

    return rangeFilteredAlerts
      .filter((alert) => String(alert.id) !== String(selectedAlert.id))
      .filter((alert) => Math.abs(new Date(alert.timestamp).getTime() - selectedTime) <= NEARBY_WINDOW_MS)
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .slice(0, 5);
  }, [rangeFilteredAlerts, selectedAlert]);

  const whyThisMatters = selectedAlert && selectedModel ? deriveWhyThisMatters(selectedAlert, selectedModel) : [];
  const timelineNodes = selectedAlert && selectedModel ? buildEventTimeline(selectedAlert, selectedModel, nearbyEvents.length) : [];
  const suggestedAction = selectedModel ? suggestAction(selectedModel.severity) : "Monitor";

  const metrics = useMemo(() => {
    const models = rangeFilteredAlerts.map((alert) => modelMap.get(String(alert.id)) ?? buildAlertCardModel(alert));
    const total = models.length;
    const criticalCount = models.filter((model) => model.severity === "CRITICAL").length;
    const threatScores = models.map((model) => model.threatScore);
    const averageThreat = total > 0 ? Math.round(threatScores.reduce((sum, score) => sum + score, 0) / total) : 0;
    const peakThreat = total > 0 ? Math.max(...threatScores) : 0;

    const typeCounts = rangeFilteredAlerts.reduce(
      (acc, alert) => {
        const normalized = normalizeEventType(alert.event_type);
        acc[normalized] = (acc[normalized] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    let topType = "none";
    let topCount = 0;
    Object.entries(typeCounts).forEach(([type, count]) => {
      if (count > topCount) {
        topType = type;
        topCount = count;
      }
    });

    const rangeMs = getRangeWindowMs(rangeFilter) ?? HOUR_MS;
    const now = Date.now();
    const currentWindowAlerts = alerts.filter((alert) => new Date(alert.timestamp).getTime() >= now - rangeMs);
    const previousWindowAlerts = alerts.filter((alert) => {
      const time = new Date(alert.timestamp).getTime();
      return time < now - rangeMs && time >= now - rangeMs * 2;
    });

    const currentCritical = currentWindowAlerts.filter((alert) => {
      const model = modelMap.get(String(alert.id)) ?? buildAlertCardModel(alert);
      return model.severity === "CRITICAL";
    }).length;

    const previousCritical = previousWindowAlerts.filter((alert) => {
      const model = modelMap.get(String(alert.id)) ?? buildAlertCardModel(alert);
      return model.severity === "CRITICAL";
    }).length;

    const totalDelta = currentWindowAlerts.length - previousWindowAlerts.length;
    const criticalDelta = currentCritical - previousCritical;

    const rangeLabel = rangeFilter === "all" ? "last 1h" : `last ${rangeFilter}`;
    const compareLabel = rangeFilter === "all" ? "previous hour" : `previous ${rangeFilter}`;

    return {
      total,
      criticalCount,
      averageThreat,
      peakThreat,
      frequentType: topCount > 0 ? formatEventLabel(topType) : "None",
      frequentTypeSubtext: topCount > 0 ? `${topCount} occurrences` : "No alerts",
      rangeLabel,
      compareLabel,
      totalDelta,
      criticalDelta,
    };
  }, [alerts, modelMap, rangeFilter, rangeFilteredAlerts]);

  function updateParams(updater: (next: URLSearchParams) => void) {
    const next = new URLSearchParams(searchParams);
    updater(next);
    setSearchParams(next, { replace: true });
  }

  function handleTypeFilter(nextType: FilterType) {
    setTypeFilter(nextType);
    updateParams((params) => {
      if (nextType === "all") {
        params.delete("type");
      } else {
        params.set("type", nextType);
      }
    });
  }

  function handleSearchChange(value: string) {
    setSearchQuery(value);
    updateParams((params) => {
      if (!value.trim()) {
        params.delete("search");
      } else {
        params.set("search", value.trim());
      }
    });
  }

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((previous) => (previous === "asc" ? "desc" : "asc"));
      return;
    }

    setSortField(field);
    setSortDir("desc");
    updateParams((params) => {
      params.set("sort", field);
    });
  }

  function selectAlert(alertId: number | string) {
    const id = String(alertId);
    setSelectedAlertId(id);
    updateParams((params) => {
      params.set("selected", id);
    });
  }

  function closeInspector() {
    setSelectedAlertId(null);
    updateParams((params) => {
      params.delete("selected");
    });
  }

  function toggleGroup(groupId: string) {
    setExpandedGroups((previous) => ({
      ...previous,
      [groupId]: !previous[groupId],
    }));
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 lg:grid-cols-5 gap-4">
        <div className="glass-card p-4 rounded-xl">
          <p className="text-xs text-textSecondary uppercase tracking-wider">Total Alerts</p>
          <p className="text-2xl font-bold text-textPrimary mt-1">{metrics.total}</p>
          <p className="text-xs text-textMuted mt-1">{`${metrics.rangeLabel} | ${metrics.totalDelta >= 0 ? "+" : ""}${metrics.totalDelta} vs ${metrics.compareLabel}`}</p>
        </div>
        <div className="glass-card p-4 rounded-xl">
          <p className="text-xs text-textSecondary uppercase tracking-wider">Critical Alerts Count</p>
          <p className="text-2xl font-bold text-textPrimary mt-1">{metrics.criticalCount}</p>
          <p className="text-xs text-textMuted mt-1">{`${metrics.rangeLabel} | ${metrics.criticalDelta >= 0 ? "+" : ""}${metrics.criticalDelta} vs ${metrics.compareLabel}`}</p>
        </div>
        <div className="glass-card p-4 rounded-xl">
          <p className="text-xs text-textSecondary uppercase tracking-wider">Average Threat Score</p>
          <p className="text-2xl font-bold text-textPrimary mt-1">{metrics.averageThreat}</p>
          <p className="text-xs text-textMuted mt-1">{metrics.rangeLabel}</p>
        </div>
        <div className="glass-card p-4 rounded-xl">
          <p className="text-xs text-textSecondary uppercase tracking-wider">Peak Threat Score</p>
          <p className="text-2xl font-bold text-textPrimary mt-1">{metrics.peakThreat}</p>
          <p className="text-xs text-textMuted mt-1">{metrics.rangeLabel}</p>
        </div>
        <div className="glass-card p-4 rounded-xl col-span-4 lg:col-span-1">
          <p className="text-xs text-textSecondary uppercase tracking-wider">Most Frequent Alert Type</p>
          <p className="text-xl font-bold text-textPrimary mt-1 truncate">{metrics.frequentType}</p>
          <p className="text-xs text-textMuted mt-1">{metrics.frequentTypeSubtext}</p>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        <aside className="col-span-12 xl:col-span-3 glass rounded-xl p-4 space-y-4">
          <div className="space-y-2">
            <p className="text-xs text-textSecondary uppercase tracking-wider">Search</p>
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface border border-border">
              <Search className="w-4 h-4 text-textSecondary" />
              <input
                type="text"
                value={searchQuery}
                onChange={(event) => handleSearchChange(event.target.value)}
                placeholder="Search by type, zone, object"
                className="bg-transparent text-sm text-textPrimary placeholder:text-textMuted outline-none w-full"
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-textSecondary" />
              <p className="text-xs text-textSecondary uppercase tracking-wider">Type</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {FILTER_TYPES.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleTypeFilter(type)}
                  className={`px-3 py-1.5 rounded-lg text-xs border transition-all duration-200 whitespace-nowrap ${
                    typeFilter === type
                      ? "bg-teal-500/20 border-teal-400 text-white"
                      : "bg-surface border-border text-textSecondary hover:text-textPrimary"
                  }`}
                >
                  {toFilterLabel(type)}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <ArrowDownUp className="w-4 h-4 text-textSecondary" />
              <p className="text-xs text-textSecondary uppercase tracking-wider">Sort</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(SORT_FIELDS as readonly SortField[]).map((field) => (
                <button
                  key={field}
                  type="button"
                  onClick={() => toggleSort(field)}
                  className={`px-3 py-1.5 rounded-lg text-xs border transition-all duration-200 text-left ${
                    sortField === field
                      ? "bg-teal-500/20 border-teal-400 text-white"
                      : "bg-surface border-border text-textSecondary hover:text-textPrimary"
                  }`}
                >
                  {field === "event_type"
                    ? "Type"
                    : field === "threat_score"
                    ? "Threat"
                    : field.charAt(0).toUpperCase() + field.slice(1)}
                  {sortField === field ? (sortDir === "asc" ? " ^" : " v") : ""}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <section className="col-span-12 xl:col-span-5 glass rounded-xl p-4">
          {isLoading ? (
            <div className="text-center text-sm text-textSecondary py-12">Loading alerts...</div>
          ) : sortedChains.length === 0 ? (
            <div className="text-center text-sm text-textSecondary py-12">No alerts match your filters</div>
          ) : (
            <div className="space-y-3 max-h-[calc(100vh-260px)] overflow-y-auto pr-1">
              {sortedChains.map((chain) => {
                const expanded = expandedGroups[chain.id] ?? chain.alerts.length <= 2;
                const DominantIcon = chain.dominantModel.icon;
                const dominantColor =
                  threatColorClasses[chain.dominantModel.severity as keyof typeof threatColorClasses] ?? "text-textPrimary";

                return (
                  <div key={chain.id} className="space-y-2">
                    {chain.alerts.length > 1 ? (
                      <button
                        type="button"
                        onClick={() => toggleGroup(chain.id)}
                        className="w-full rounded-lg bg-surface border border-border px-3 py-2 transition-all duration-200 hover:scale-[1.01]"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <DominantIcon className={`w-4 h-4 ${dominantColor}`} />
                            <span className="text-sm font-semibold text-textPrimary">{`${chain.alerts.length} related events`}</span>
                          </div>
                          <span className="text-textSecondary">
                            {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </span>
                        </div>
                        <p className="mt-1 text-left text-xs text-textMuted">
                          {`${formatChainRange(chain.startMs, chain.endMs)} | ${formatEventLabel(chain.dominantType)}`}
                        </p>
                      </button>
                    ) : null}

                    <div
                      className={`overflow-hidden transition-all duration-200 ${
                        expanded || chain.alerts.length <= 1 ? "max-h-[1600px] opacity-100" : "max-h-0 opacity-0"
                      }`}
                    >
                      <div className={`space-y-2 pt-1 ${chain.alerts.length > 1 ? "border-l border-border/60 pl-4 opacity-90" : ""}`}>
                        {chain.alerts.map((alert) => (
                          <AlertCard
                            key={alert.id}
                            alert={alert}
                            selected={String(alert.id) === selectedAlertId}
                            showSnapshot={false}
                            onClick={selectAlert}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <aside className="col-span-12 xl:col-span-4 glass rounded-xl p-4">
          {selectedAlert && selectedModel ? (
            <div className={`space-y-5 transition-opacity duration-200 ${inspectorVisible ? "opacity-100" : "opacity-0"}`}>
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <p className="text-sm font-semibold text-textPrimary truncate">{selectedModel.title}</p>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-semibold uppercase border whitespace-nowrap ${
                      threatColorClasses[selectedModel.severity as keyof typeof threatColorClasses]
                    } ${threatBadgeBgClasses[selectedModel.severity as keyof typeof threatBadgeBgClasses]}`}
                  >
                    {selectedModel.severity}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={closeInspector}
                  className="p-2 rounded-lg bg-surface border border-border text-textSecondary hover:text-textPrimary transition-all duration-200"
                  aria-label="Close inspector"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <SnapshotInvestigation
                src={selectedModel.snapshotSrc}
                eventTitle={selectedModel.title}
                severity={selectedModel.severity}
                timestamp={selectedAlert.timestamp}
              />

              <div className="glass-card rounded-xl p-3 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-textSecondary">Time</span>
                  <span className="text-textPrimary">{new Date(selectedAlert.timestamp).toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-textSecondary">Threat Score</span>
                  <span className="text-textPrimary font-semibold">{selectedModel.threatScore}</span>
                </div>
                {selectedModel.zone !== "--" ? (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-textSecondary">Zone</span>
                    <span className="text-textPrimary">{selectedModel.zone}</span>
                  </div>
                ) : null}
                {selectedModel.objectLabel ? (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-textSecondary">Object</span>
                    <span className="text-textPrimary">{selectedModel.objectLabel}</span>
                  </div>
                ) : null}
              </div>

              <div className="glass-card rounded-xl p-3 space-y-2">
                <p className="text-xs text-textSecondary uppercase tracking-wider">WHY THIS ALERT MATTERS</p>
                <div className="space-y-1">
                  {whyThisMatters.map((reason) => (
                    <p key={reason} className="text-sm text-textPrimary">
                      {reason}
                    </p>
                  ))}
                </div>
              </div>

              <div className="glass-card rounded-xl p-3 space-y-3">
                <p className="text-xs text-textSecondary uppercase tracking-wider">EVENT TIMELINE</p>
                <div className="flex items-center gap-2 overflow-x-auto pb-1">
                  {timelineNodes.map((node, index) => (
                    <div key={node.key} className="flex items-center shrink-0">
                      <div className="rounded-lg border border-border bg-surface px-3 py-1.5">
                        <p className="text-xs font-semibold text-textPrimary">{node.label}</p>
                        <p className="text-xs text-textMuted">{node.detail}</p>
                      </div>
                      {index < timelineNodes.length - 1 ? <span className="mx-2 text-textMuted">----</span> : null}
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass-card rounded-xl p-3 space-y-3">
                <p className="text-xs text-textSecondary uppercase tracking-wider">NEARBY EVENTS</p>
                {nearbyEvents.length > 0 ? (
                  <div className="space-y-2 border-t border-border/50 pt-2">
                    {nearbyEvents.map((alert) => (
                      <div key={alert.id} className="opacity-75 transition-all duration-200 hover:opacity-95">
                        <AlertCard
                          alert={alert}
                          compact
                          minimal
                          showSnapshot={false}
                          onClick={selectAlert}
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-textMuted">No nearby events within +/-20 seconds.</p>
                )}
              </div>

              <div className="glass-card rounded-xl p-3 space-y-2">
                <p className="text-xs text-textSecondary uppercase tracking-wider">Suggested Action</p>
                <div className="grid grid-cols-3 gap-2">
                  {(["Monitor", "Escalate", "Ignore"] as const).map((option) => (
                    <div
                      key={option}
                      className={`rounded-lg border px-2 py-1.5 text-center text-xs ${
                        option === suggestedAction
                          ? "bg-teal-500/20 border-teal-400 text-white"
                          : "bg-surface border-border text-textSecondary"
                      }`}
                    >
                      {option}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[520px] flex items-center justify-center opacity-60">
              <div className="text-center space-y-2">
                <AlertTriangle className="w-8 h-8 text-textMuted mx-auto" />
                <p className="text-sm text-textPrimary">Select an alert to inspect details</p>
                <p className="text-xs text-textSecondary">View snapshot, threat score, and context</p>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
