import { useState } from "react";
import { useAlerts } from "../hooks/useAlerts";
import { API } from "../api/config";
import { AlertTriangle, ShieldAlert, Eye, Users, Filter, Search, Crosshair } from "lucide-react";

const eventIcons: Record<string, typeof AlertTriangle> = {
  intrusion: ShieldAlert,
  loitering: Eye,
  crowd: Users,
  dangerous_object: Crosshair,
};

type SortField = "timestamp" | "event_type" | "zone";
type SortDir = "asc" | "desc";

export default function Alerts() {
  const { data, isLoading } = useAlerts(200);
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("timestamp");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [selectedSnapshot, setSelectedSnapshot] = useState<string | null>(null);

  const alerts = data?.alerts ?? [];

  // Priority: weapon > intrusion > loitering > crowd > other
  const eventPriority: Record<string, number> = {
    dangerous_object: 0,
    intrusion: 1,
    loitering: 2,
    crowd: 3,
  };

  const filtered = alerts
    .filter((a) => typeFilter === "all" || a.event_type === typeFilter)
    .filter(
      (a) =>
        !searchQuery ||
        a.event_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        a.zone?.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      // Priority sort first
      const pa = eventPriority[a.event_type] ?? 9;
      const pb = eventPriority[b.event_type] ?? 9;
      if (pa !== pb) return pa - pb;
      // Then user-chosen sort
      const valA = a[sortField] ?? "";
      const valB = b[sortField] ?? "";
      const cmp = String(valA).localeCompare(String(valB));
      return sortDir === "asc" ? cmp : -cmp;
    });

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  return (
    <div className="space-y-5">
      {/* Header + Filters */}
      <div className="rounded-2xl glass-panel p-5">
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.06)] flex-1 min-w-[200px]">
            <Search className="w-4 h-4 text-ow-mist/35" />
            <input
              type="text"
              placeholder="Search alerts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent text-sm text-ow-light/80 placeholder:text-ow-mist/25 outline-none w-full"
            />
          </div>

          {/* Type filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-ow-mist/35" />
            {["all", "intrusion", "loitering", "crowd", "dangerous_object"].map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  typeFilter === t
                    ? "bg-ow-accent/15 text-ow-accent border border-ow-accent/25"
                    : "bg-ow-teal/8 text-ow-mist/45 border border-[rgba(255,255,255,0.04)] hover:bg-ow-teal/15 hover:text-ow-mist/70"
                }`}
              >
                {t === "all" ? "All" : t === "dangerous_object" ? "Weapons" : t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            {(["timestamp", "event_type", "zone"] as SortField[]).map((f) => (
              <button
                key={f}
                onClick={() => toggleSort(f)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  sortField === f
                    ? "bg-ow-teal/15 text-ow-light/80 border border-[rgba(255,255,255,0.08)]"
                    : "bg-ow-teal/8 text-ow-mist/35 border border-[rgba(255,255,255,0.04)] hover:text-ow-mist/60"
                }`}
              >
                {f === "event_type" ? "Type" : f.charAt(0).toUpperCase() + f.slice(1)}
                {sortField === f && (sortDir === "asc" ? " ↑" : " ↓")}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Alert list */}
      <div className="rounded-2xl glass-panel p-5">
        {isLoading ? (
          <div className="text-center text-ow-mist/30 py-12">Loading alerts...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center text-ow-mist/30 py-12">No alerts match your filters</div>
        ) : (
          <div className="space-y-2">
            {filtered.map((alert) => {
              const Icon = eventIcons[alert.event_type] ?? AlertTriangle;
              const snapshotFile = alert.snapshot_path?.split("/").pop() ?? "";
              const isWeapon = alert.event_type === "dangerous_object";
              return (
                <div
                  key={alert.id}
                  className={`flex items-center gap-4 p-4 rounded-xl transition-all cursor-pointer ${
                    isWeapon
                      ? "bg-red-500/10 border-2 border-red-500/30 hover:bg-red-500/15 hover:border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.15)]"
                      : "bg-ow-teal/8 border border-[rgba(255,255,255,0.04)] hover:bg-ow-teal/15 hover:border-ow-accent/10"
                  }`}
                  onClick={() => snapshotFile && setSelectedSnapshot(snapshotFile)}
                >
                  {snapshotFile && (
                    <img
                      src={API.snapshots(snapshotFile)}
                      alt="snapshot"
                      className="w-16 h-16 rounded-lg object-cover flex-shrink-0 border border-[rgba(255,255,255,0.08)]"
                      loading="lazy"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className="w-4 h-4 text-ow-accent" />
                      <span className="text-sm font-semibold capitalize text-ow-light/90">
                        {alert.event_type === "dangerous_object" ? "Weapon" : alert.event_type}
                      </span>
                      {alert.event_type === "dangerous_object" && typeof alert.metadata?.object_type === "string" ? (
                        <span className="px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 text-[10px] font-bold uppercase">
                          {alert.metadata.object_type}
                        </span>
                      ) : null}
                    </div>
                    <div className="text-xs text-ow-mist/45">
                      {alert.event_type === "dangerous_object"
                        ? `Object: ${alert.metadata?.object_type ?? "—"} · Confidence: ${
                            typeof alert.metadata?.confidence === "number"
                              ? `${(Number(alert.metadata.confidence) * 100).toFixed(0)}%`
                              : "—"
                          }`
                        : `Zone: ${alert.zone || "—"} · Track #${alert.track_id ?? "—"}`}
                    </div>
                  </div>
                  <div className="text-xs text-ow-mist/25 font-mono whitespace-nowrap">
                    {new Date(alert.timestamp).toLocaleString()}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Snapshot preview modal */}
      {selectedSnapshot && (
        <div
          className="fixed inset-0 z-50 bg-ow-bg/70 backdrop-blur-sm flex items-center justify-center p-8"
          onClick={() => setSelectedSnapshot(null)}
        >
          <div className="max-w-3xl max-h-[80vh] rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
            <img
              src={API.snapshots(selectedSnapshot)}
              alt="Alert Snapshot"
              className="w-full h-full object-contain"
            />
          </div>
        </div>
      )}
    </div>
  );
}
