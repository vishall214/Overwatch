import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileClock, FileText, Mail, RefreshCcw } from "lucide-react";

import {
  downloadReport,
  generateReport,
  getReport,
  getReportSchedulerStatus,
  listReports,
  type ReportListItem,
  type ReportPeriod,
} from "../services/reportsService";
import { formatEventLabel, normalizeEventType } from "../utils/normalization";
import { normalizeThreatLevel } from "../utils/threat";
import { threatBadgeBgClasses, threatBorderClasses, threatTextClasses } from "../theme/threat";

const WEEKDAY_LABELS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

export default function Reports() {
  const queryClient = useQueryClient();
  const [selectedReportId, setSelectedReportId] = useState<string>("");
  const [downloadError, setDownloadError] = useState<string>("");

  const reportsQuery = useQuery({
    queryKey: ["reports"],
    queryFn: () => listReports(60),
    refetchInterval: 15000,
  });

  const schedulerQuery = useQuery({
    queryKey: ["reportsScheduler"],
    queryFn: getReportSchedulerStatus,
    refetchInterval: 30000,
  });

  const selectedReportQuery = useQuery({
    queryKey: ["reportDetails", selectedReportId],
    queryFn: () => getReport(selectedReportId),
    enabled: Boolean(selectedReportId),
  });

  const generateMutation = useMutation({
    mutationFn: (period: ReportPeriod) => generateReport(period),
    onSuccess: (response) => {
      const generatedId = response.data?.id;
      void queryClient.invalidateQueries({ queryKey: ["reports"] });
      void queryClient.invalidateQueries({ queryKey: ["reportsScheduler"] });
      if (generatedId) {
        setSelectedReportId(generatedId);
      }
    },
  });

  const reports = reportsQuery.data?.data ?? [];
  const selectedPayload = selectedReportQuery.data?.data;

  useEffect(() => {
    if (!reports.length) return;
    if (!selectedReportId) {
      setSelectedReportId(reports[0].id);
      return;
    }
    const stillExists = reports.some((report) => report.id === selectedReportId);
    if (!stillExists) {
      setSelectedReportId(reports[0].id);
    }
  }, [reports, selectedReportId]);

  const scheduler = schedulerQuery.data?.data;
  const summary = selectedPayload?.summary;
  const recentEvents = useMemo(
    () => (selectedPayload?.recent_events ?? []).slice(0, 15),
    [selectedPayload?.recent_events]
  );

  async function handleDownload(format: "json" | "csv") {
    if (!selectedPayload) return;
    setDownloadError("");
    try {
      const { blob, filename } = await downloadReport(selectedPayload.report_id, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "Failed to download report");
    }
  }

  return (
    <div className="space-y-5">
      <header className="panel-base rounded-lg p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-textPrimary">Reports</h1>
            <p className="text-sm text-textSecondary mt-1">
              Generate daily and weekly summaries, then export JSON/CSV artifacts.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => generateMutation.mutate("daily")}
              disabled={generateMutation.isPending}
              className="px-4 py-2 rounded-lg bg-accent/10 border border-accent/30 text-accent text-sm font-semibold hover:bg-accent/20 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              Generate Daily
            </button>
            <button
              onClick={() => generateMutation.mutate("weekly")}
              disabled={generateMutation.isPending}
              className="px-4 py-2 rounded-lg bg-threat-info/10 border border-threat-info/30 text-threat-info text-sm font-semibold hover:bg-threat-info/20 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              Generate Weekly
            </button>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <StatusBadge
            icon={<RefreshCcw className="w-4 h-4" />}
            label="Scheduler"
            value={scheduler?.running ? "Running" : scheduler?.enabled ? "Enabled" : "Disabled"}
            tone={scheduler?.running ? "ok" : scheduler?.enabled ? "warn" : "muted"}
          />
          <StatusBadge
            icon={<FileClock className="w-4 h-4" />}
            label="Daily UTC"
            value={scheduler?.daily_time_utc || "--:--"}
            tone="muted"
          />
          <StatusBadge
            icon={<FileText className="w-4 h-4" />}
            label="Weekly Day"
            value={WEEKDAY_LABELS[scheduler?.weekly_day_utc ?? 0] ?? "Monday"}
            tone="muted"
          />
          <StatusBadge
            icon={<Mail className="w-4 h-4" />}
            label="Email"
            value={scheduler?.email_enabled ? `Enabled (${scheduler.email_recipients_count})` : "Disabled"}
            tone={scheduler?.email_enabled ? "ok" : "muted"}
          />
        </div>

        {generateMutation.isError ? (
          <p className="mt-3 text-xs text-threat-critical">Failed to generate report.</p>
        ) : null}
      </header>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
        <section className="xl:col-span-4 panel-base rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm uppercase tracking-wider text-textSecondary font-semibold">Available Reports</h2>
            <span className="text-xs text-textMuted">{reports.length}</span>
          </div>

          {reportsQuery.isLoading ? (
            <p className="text-sm text-textSecondary">Loading reports...</p>
          ) : reports.length === 0 ? (
            <p className="text-sm text-textSecondary">No reports generated yet.</p>
          ) : (
            <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
              {reports.map((report) => (
                <ReportListRow
                  key={report.id}
                  report={report}
                  selected={report.id === selectedReportId}
                  onSelect={() => setSelectedReportId(report.id)}
                />
              ))}
            </div>
          )}
        </section>

        <section className="xl:col-span-8 panel-base rounded-lg p-5">
          {!selectedReportId ? (
            <p className="text-sm text-textSecondary">Select a report to inspect details.</p>
          ) : selectedReportQuery.isLoading ? (
            <p className="text-sm text-textSecondary">Loading report details...</p>
          ) : !selectedPayload ? (
            <p className="text-sm text-textSecondary">Unable to load selected report.</p>
          ) : (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold text-textPrimary">{selectedPayload.report_id}</h2>
                  <p className="text-xs text-textSecondary mt-1">
                    {selectedPayload.period.toUpperCase()} • {new Date(selectedPayload.generated_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => void handleDownload("json")}
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-accent/10 border border-accent/30 text-accent text-xs font-semibold"
                  >
                    <Download className="w-3.5 h-3.5" /> JSON
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDownload("csv")}
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-threat-info/10 border border-threat-info/30 text-threat-info text-xs font-semibold"
                  >
                    <Download className="w-3.5 h-3.5" /> CSV
                  </button>
                </div>
              </div>

              {downloadError ? (
                <p className="text-xs text-threat-critical">{downloadError}</p>
              ) : null}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <MetricCard label="Total" value={summary?.total ?? 0} />
                <MetricCard label="Intrusion" value={summary?.intrusion ?? 0} />
                <MetricCard label="Loitering" value={summary?.loitering ?? 0} />
                <MetricCard label="Crowd" value={summary?.crowd ?? 0} />
                <MetricCard label="Weapon Detected" value={summary?.weapon_detected ?? 0} />
                <MetricCard label="Weapon In Zone" value={summary?.weapon_in_zone ?? 0} />
                <MetricCard label="Avg Threat" value={Math.round(summary?.avg_threat_score ?? 0)} />
                <MetricCard label="Peak Threat" value={summary?.peak_threat_score ?? 0} />
              </div>

              <div>
                <h3 className="text-sm uppercase tracking-wider text-textSecondary mb-2">Recent Events</h3>
                {recentEvents.length === 0 ? (
                  <p className="text-sm text-textSecondary">No events captured in this report window.</p>
                ) : (
                  <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                    {recentEvents.map((event) => {
                      const level = normalizeThreatLevel(event.threat_level);
                      const borderClass = threatBorderClasses[level];
                      const bgClass = threatBadgeBgClasses[level];
                      const textClass = threatTextClasses[level];

                      return (
                        <div
                          key={`${event.id}-${event.timestamp}`}
                          className={`card-base border ${borderClass} ${bgClass}`}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-sm font-semibold text-textPrimary">
                              {formatEventLabel(normalizeEventType(event.event_type))}
                            </span>
                            <span className={`text-[10px] uppercase font-bold ${textClass}`}>
                              {level}
                            </span>
                          </div>
                          <p className="text-xs text-textSecondary mt-1">
                            Zone: {event.zone || "--"} • Track: {event.track_id ?? "--"}
                          </p>
                          <p className="text-xs text-textMuted mt-1 font-mono">
                            Score {event.threat_score} • {new Date(event.timestamp).toLocaleString()}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="card-base">
      <p className="text-[11px] uppercase tracking-wider text-textMuted">{label}</p>
      <p className="text-lg font-bold text-textPrimary mt-1">{value}</p>
    </div>
  );
}

function StatusBadge({
  icon,
  label,
  value,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone: "ok" | "warn" | "muted";
}) {
  const toneClass =
    tone === "ok"
      ? "border-accent/30 bg-accent/10 text-accent"
      : tone === "warn"
      ? "border-threat-high/30 bg-threat-high/10 text-threat-high"
      : "border-border bg-surface text-textSecondary";

  return (
    <div className={`rounded-lg border px-3 py-2 ${toneClass}`}>
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider font-semibold">
        {icon}
        <span>{label}</span>
      </div>
      <p className="text-xs mt-1 text-textPrimary">{value}</p>
    </div>
  );
}

function ReportListRow({
  report,
  selected,
  onSelect,
}: {
  report: ReportListItem;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left rounded-xl border px-3 py-3 transition-colors ${
        selected
          ? "border-accent/40 bg-accent/10"
          : "border-border bg-surface hover:border-accent/30"
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-textPrimary">{report.period.toUpperCase()}</span>
        <span className="text-[10px] uppercase tracking-wide text-textMuted">{report.trigger}</span>
      </div>
      <p className="text-xs text-textSecondary mt-1">{new Date(report.generated_at).toLocaleString()}</p>
      <p className="text-xs text-textMuted mt-2">
        Alerts: {report.summary.total ?? 0} • Peak: {report.summary.peak_threat_score ?? 0}
      </p>
    </button>
  );
}
