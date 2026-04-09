import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, ArrowDownUp, ChevronDown, ChevronRight, Filter, Search, X } from "lucide-react";
import { AlertCard, buildAlertCardModel, type AlertItem } from "../components/AlertsPanel";
import { useAlerts } from "../hooks/useAlerts";
import { formatEventLabel, normalizeEventType } from "../utils/normalization";
import { threatBadgeBgClasses, threatColorClasses } from "../theme/threat";

type SortField = "timestamp" | "event_type" | "zone" | "threat_score";
type SortDir = "asc" | "desc";

type AlertGroup = {
  id: string;
  eventType: string;
  alerts: AlertItem[];
};

const FILTER_TYPES = ["all", "intrusion", "loitering", "crowd", "weapon_detected", "weapon_in_zone"] as const;
const SORT_FIELDS = ["timestamp", "event_type", "zone", "threat_score"] as const;
const GROUP_WINDOW_MS = 8000;

const persistenceMetadataKeys = ["duration_s", "duration_seconds", "dwell_seconds", "loitering_seconds", "persistence_seconds"] as const;

function toFilterLabel(value: (typeof FILTER_TYPES)[number]) {
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

function getPersistenceSeconds(metadata: Record<string, unknown>): number | null {
  for (const key of persistenceMetadataKeys) {
    const value = parseNumber(metadata[key]);
    if (value !== null) return value;
  }
  return null;
}

function deriveWhyThisMatters(alert: AlertItem, threatScore: number, zone: string): string[] {
  const eventType = normalizeEventType(alert.event_type);
  const metadata = (alert.metadata as Record<string, unknown>) ?? {};
  const reasons: string[] = [];

  if (eventType === "weapon_in_zone") {
    reasons.push(zone !== "--" ? `Weapon detected inside ${zone}.` : "Weapon detected inside a monitored zone.");
  } else if (eventType === "weapon_detected") {
    reasons.push("Weapon-like object detected by the active module.");
  } else if (eventType === "intrusion") {
    reasons.push(zone !== "--" ? `Intrusion detected in ${zone}.` : "Intrusion detected in a monitored area.");
  } else if (eventType === "loitering") {
    reasons.push(zone !== "--" ? `Extended presence detected in ${zone}.` : "Extended presence detected in a monitored area.");
  } else if (eventType === "crowd") {
    reasons.push(zone !== "--" ? `Crowd activity detected in ${zone}.` : "Crowd activity detected in a monitored area.");
  } else {
    reasons.push(`${formatEventLabel(eventType)} event requires operator review.`);
  }

  const persistence = getPersistenceSeconds(metadata);
  if (persistence !== null && persistence >= 5) {
    reasons.push(`Activity persisted for ${Math.round(persistence)} seconds.`);
  }

  if (threatScore >= 80) {
    reasons.push(`Threat score reached ${threatScore}, indicating elevated risk.`);
  }

  return reasons.slice(0, 2);
}

function buildTimeline(alert: AlertItem, severity: string) {
  const metadata = (alert.metadata as Record<string, unknown>) ?? {};
  const detectedAt = new Date(alert.timestamp);
  const persistence = getPersistenceSeconds(metadata);

  return [
    {
      key: "detected",
      label: "detected",
      detail: detectedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    },
    {
      key: "persisted",
      label: "persisted",
      detail: persistence !== null ? `${Math.round(persistence)}s observed` : "No persistence signal",
    },
    {
      key: "escalated",
      label: "escalated",
      detail:
        severity === "CRITICAL" || severity === "HIGH"
          ? `Escalated to ${severity}`
          : `Severity remained ${severity}`,
    },
  ];
}

function suggestAction(severity: string): "Monitor" | "Escalate" | "Ignore" {
  if (severity === "CRITICAL" || severity === "HIGH") return "Escalate";
  if (severity === "MEDIUM") return "Monitor";
  return "Ignore";
}

function SnapshotInspector({ src }: { src: string | null }) {
  const [broken, setBroken] = useState(false);

  useEffect(() => {
    setBroken(false);
  }, [src]);

  if (!src || broken) {
    return (
      <div className="w-full aspect-video rounded-xl bg-surface border border-border flex items-center justify-center">
        <AlertTriangle className="w-5 h-5 text-textMuted" />
      </div>
    );
  }

  return (
    <div className="w-full aspect-video rounded-xl border border-border overflow-hidden bg-surface">
      <img
        src={src}
        alt="Selected alert snapshot"
        className="w-full h-full object-cover transition-transform duration-200 hover:scale-[1.02]"
        onError={() => setBroken(true)}
      />
    </div>
  );
}

export default function Alerts() {
  const { data, isLoading } = useAlerts(200);
  const [searchParams, setSearchParams] = useSearchParams();

  const requestedType = searchParams.get("type");
  const requestedSort = searchParams.get("sort");
  const initialType =
    requestedType && FILTER_TYPES.includes(requestedType as (typeof FILTER_TYPES)[number]) ? requestedType : "all";
  const initialSort =
    requestedSort && SORT_FIELDS.includes(requestedSort as (typeof SORT_FIELDS)[number])
      ? (requestedSort as SortField)
      : "timestamp";

  const [typeFilter, setTypeFilter] = useState<string>(initialType);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>(initialSort);
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(searchParams.get("selected"));
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const nextType = searchParams.get("type");
    setTypeFilter(nextType && FILTER_TYPES.includes(nextType as (typeof FILTER_TYPES)[number]) ? nextType : "all");

    const nextSort = searchParams.get("sort");
    if (nextSort && SORT_FIELDS.includes(nextSort as (typeof SORT_FIELDS)[number])) {
      setSortField(nextSort as SortField);
    }

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

  const metrics = useMemo(() => {
    const models = alerts.map((alert) => modelMap.get(String(alert.id)) ?? buildAlertCardModel(alert));
    const total = models.length;
    const criticalCount = models.filter((model) => model.severity === "CRITICAL").length;
    const threatScores = models.map((model) => model.threatScore);
    const averageThreat = total > 0 ? Math.round(threatScores.reduce((sum, score) => sum + score, 0) / total) : 0;
    const peakThreat = total > 0 ? Math.max(...threatScores) : 0;

    const typeCounts = alerts.reduce(
      (acc, alert) => {
        const normalized = normalizeEventType(alert.event_type);
        acc[normalized] = (acc[normalized] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    let topType = "none";
    let topCount = 0;
    for (const [type, count] of Object.entries(typeCounts)) {
      if (count > topCount) {
        topType = type;
        topCount = count;
      }
    }

    return {
      total,
      criticalCount,
      averageThreat,
      peakThreat,
      frequentType: topCount > 0 ? formatEventLabel(topType) : "None",
      frequentTypeSubtext: topCount > 0 ? `${topCount} occurrences` : "No alerts",
    };
  }, [alerts, modelMap]);

  const filteredSorted = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    const filtered = alerts
      .filter((alert) => typeFilter === "all" || normalizeEventType(alert.event_type) === typeFilter)
      .filter((alert) => {
        if (!query) return true;
        const model = modelMap.get(String(alert.id)) ?? buildAlertCardModel(alert);
        const searchFields = [model.title, model.zone, model.objectLabel ?? "", model.contextText].join(" ").toLowerCase();
        return searchFields.includes(query);
      });

    return [...filtered].sort((a, b) => {
      let cmp = 0;
      const aModel = modelMap.get(String(a.id)) ?? buildAlertCardModel(a);
      const bModel = modelMap.get(String(b.id)) ?? buildAlertCardModel(b);

      if (sortField === "timestamp") {
        cmp = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
      } else if (sortField === "event_type") {
        cmp = normalizeEventType(a.event_type).localeCompare(normalizeEventType(b.event_type));
      } else if (sortField === "zone") {
        cmp = (a.zone ?? "").localeCompare(b.zone ?? "");
      } else {
        cmp = aModel.threatScore - bModel.threatScore;
      }

      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [alerts, modelMap, searchQuery, sortDir, sortField, typeFilter]);

  const groupedAlerts = useMemo(() => {
    const groups: AlertGroup[] = [];
    const groupLastTimestamp: number[] = [];

    filteredSorted.forEach((alert, index) => {
      const eventType = normalizeEventType(alert.event_type);
      const timestamp = new Date(alert.timestamp).getTime();
      const previousGroup = groups[groups.length - 1];
      const previousTimestamp = groupLastTimestamp[groupLastTimestamp.length - 1];

      if (
        previousGroup &&
        previousGroup.eventType === eventType &&
        Number.isFinite(previousTimestamp) &&
        Math.abs(previousTimestamp - timestamp) <= GROUP_WINDOW_MS
      ) {
        previousGroup.alerts.push(alert);
        groupLastTimestamp[groupLastTimestamp.length - 1] = timestamp;
        return;
      }

      groups.push({
        id: `${eventType}-${timestamp}-${index}`,
        eventType,
        alerts: [alert],
      });
      groupLastTimestamp.push(timestamp);
    });

    return groups;
  }, [filteredSorted]);

  useEffect(() => {
    const defaults: Record<string, boolean> = {};
    groupedAlerts.forEach((group) => {
      defaults[group.id] = group.alerts.length <= 2;
    });
    setExpandedGroups(defaults);
  }, [groupedAlerts]);

  const selectedAlert = useMemo(() => {
    if (!selectedAlertId) return null;
    return filteredSorted.find((alert) => String(alert.id) === selectedAlertId) ?? null;
  }, [filteredSorted, selectedAlertId]);

  const selectedModel = selectedAlert ? modelMap.get(String(selectedAlert.id)) ?? buildAlertCardModel(selectedAlert) : null;
  const whyThisMatters =
    selectedAlert && selectedModel
      ? deriveWhyThisMatters(selectedAlert, selectedModel.threatScore, selectedModel.zone)
      : [];
  const timeline =
    selectedAlert && selectedModel ? buildTimeline(selectedAlert, selectedModel.severity) : [];
  const action = selectedModel ? suggestAction(selectedModel.severity) : "Monitor";

  function updateParams(updater: (next: URLSearchParams) => void) {
    const next = new URLSearchParams(searchParams);
    updater(next);
    setSearchParams(next, { replace: true });
  }

  function handleTypeFilter(nextType: string) {
    setTypeFilter(nextType);
    updateParams((params) => {
      if (nextType === "all") {
        params.delete("type");
      } else {
        params.set("type", nextType);
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
          <p className="text-xs text-textMuted mt-1">Current dataset</p>
        </div>
        <div className="glass-card p-4 rounded-xl">
          <p className="text-xs text-textSecondary uppercase tracking-wider">Critical Alerts Count</p>
          <p className="text-2xl font-bold text-textPrimary mt-1">{metrics.criticalCount}</p>
          <p className="text-xs text-textMuted mt-1">Immediate attention</p>
        </div>
        <div className="glass-card p-4 rounded-xl">
          <p className="text-xs text-textSecondary uppercase tracking-wider">Average Threat Score</p>
          <p className="text-2xl font-bold text-textPrimary mt-1">{metrics.averageThreat}</p>
          <p className="text-xs text-textMuted mt-1">Across all alerts</p>
        </div>
        <div className="glass-card p-4 rounded-xl">
          <p className="text-xs text-textSecondary uppercase tracking-wider">Peak Threat Score</p>
          <p className="text-2xl font-bold text-textPrimary mt-1">{metrics.peakThreat}</p>
          <p className="text-xs text-textMuted mt-1">Highest observed</p>
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
                onChange={(event) => setSearchQuery(event.target.value)}
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
                  className={`px-3 py-1.5 rounded-lg text-xs border transition-colors whitespace-nowrap ${
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
                  className={`px-3 py-1.5 rounded-lg text-xs border transition-colors text-left ${
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
          ) : groupedAlerts.length === 0 ? (
            <div className="text-center text-sm text-textSecondary py-12">No alerts match your filters</div>
          ) : (
            <div className="space-y-3 max-h-[calc(100vh-260px)] overflow-y-auto pr-1">
              {groupedAlerts.map((group) => {
                const expanded = expandedGroups[group.id] ?? group.alerts.length <= 2;
                const groupLabel = formatEventLabel(group.eventType);

                return (
                  <div key={group.id} className="space-y-2">
                    {group.alerts.length > 1 ? (
                      <button
                        type="button"
                        onClick={() => toggleGroup(group.id)}
                        className="w-full flex items-center justify-between rounded-lg bg-surface border border-border px-3 py-2"
                      >
                        <span className="text-sm font-semibold text-textPrimary">{`[ ${group.alerts.length} ${groupLabel} Alerts ]`}</span>
                        <span className="text-textSecondary">
                          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </span>
                      </button>
                    ) : null}

                    {expanded || group.alerts.length <= 1 ? (
                      <div className="space-y-2">
                        {group.alerts.map((alert) => (
                          <AlertCard
                            key={alert.id}
                            alert={alert}
                            selected={String(alert.id) === selectedAlertId}
                            showSnapshot={false}
                            onClick={selectAlert}
                          />
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <aside className="col-span-12 xl:col-span-4 glass rounded-xl p-4">
          {selectedAlert && selectedModel ? (
            <div className="space-y-4">
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
                  className="p-2 rounded-lg bg-surface border border-border text-textSecondary hover:text-textPrimary"
                  aria-label="Close inspector"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <SnapshotInspector src={selectedModel.snapshotSrc} />

              <div className="glass-card rounded-xl p-3 space-y-2">
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

              <div className="glass-card rounded-xl p-3 space-y-2">
                <p className="text-xs text-textSecondary uppercase tracking-wider">Mini Timeline</p>
                <ul className="space-y-2">
                  {timeline.map((item) => (
                    <li key={item.key} className="flex items-start gap-2">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-teal-400 flex-shrink-0" />
                      <div>
                        <p className="text-xs uppercase text-textSecondary tracking-wider">{item.label}</p>
                        <p className="text-sm text-textPrimary">{item.detail}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="glass-card rounded-xl p-3 space-y-2">
                <p className="text-xs text-textSecondary uppercase tracking-wider">Suggested Action</p>
                <div className="grid grid-cols-3 gap-2">
                  {(["Monitor", "Escalate", "Ignore"] as const).map((option) => (
                    <div
                      key={option}
                      className={`rounded-lg border px-2 py-1.5 text-center text-xs ${
                        option === action
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
