import React, { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { Activity, AlertTriangle, BarChart3, Radar } from "lucide-react";
import {
  getAlertsOverTime,
  getDistribution,
  getSummary,
  getRecentAlerts,
  getThreatMetrics,
  type AlertRecord,
} from "../services/analyticsService";
import { formatEventLabel, normalizeEventType } from "../utils/normalization";
import { colors } from "../theme/colors";
import { threatFillClasses, threatTextClasses } from "../theme/threat";
import { useSystemStatus } from "../hooks/useSystemStatus";

const EVENT_CONFIG = {
  intrusion: { label: "Intrusion", color: colors.threat.critical, dotClass: "bg-threat-critical" },
  loitering: { label: "Loitering", color: colors.threat.high, dotClass: "bg-threat-high" },
  crowd: { label: "Crowd", color: colors.threat.info, dotClass: "bg-threat-info" },
  weapon_detected: { label: "Weapon Detected", color: colors.threat.high, dotClass: "bg-threat-high" },
  weapon_in_zone: { label: "Weapon In Zone", color: colors.threat.critical, dotClass: "bg-threat-critical" },
  dangerous_object: { label: "Dangerous Object", color: colors.threat.high, dotClass: "bg-threat-high" },
};

type EventKey = keyof typeof EVENT_CONFIG;

interface SummaryCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  denom?: string;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ title, value, icon, denom }) => (
  <div className="card-base">
    <div className="flex items-start justify-between mb-2">
      <div>
        <p className="text-xs text-textSecondary uppercase">{title}</p>
        <p className="text-lg font-semibold text-textPrimary mt-1">{value}</p>
        {denom && <p className="text-xs text-textSecondary mt-1">{denom}</p>}
      </div>
      <div className="w-8 h-8 rounded-lg border border-border bg-surface flex items-center justify-center text-textSecondary">
        {icon}
      </div>
    </div>
  </div>
);

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; name: string }>;
  label?: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="panel-base rounded-lg p-2">
        <p className="text-xs text-textSecondary">{label}</p>
        <p className="text-sm font-semibold text-textPrimary">{payload[0].value}</p>
      </div>
    );
  }
  return null;
};

interface RecentAlertItemProps {
  alert: AlertRecord;
}

const RecentAlertItem: React.FC<RecentAlertItemProps> = ({ alert }) => {
  const normalizedType = normalizeEventType(alert.event_type);
  const dotClass = EVENT_CONFIG[normalizedType as EventKey]?.dotClass ?? "bg-textMuted";
  const time = new Date(alert.timestamp);
  const timeStr = time.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div className="card-base flex items-center gap-3">
      <div className={`w-3 h-3 rounded-full flex-shrink-0 ${dotClass}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-textPrimary capitalize">{formatEventLabel(normalizedType)}</p>
        <p className="text-xs text-textSecondary">{alert.zone}</p>
      </div>
      <p className="text-xs text-textMuted flex-shrink-0">{timeStr}</p>
    </div>
  );
};

export default function Analytics() {
  const navigate = useNavigate();
  const [timeRange, setTimeRange] = useState<"1h" | "6h" | "24h">("24h");
  const [pendingAlertsPath, setPendingAlertsPath] = useState<string | null>(null);
  const pollInterval = 5000;
  const { data: systemStatus } = useSystemStatus();

  useEffect(() => {
    if (!pendingAlertsPath) return;

    const timer = window.setTimeout(() => {
      navigate(pendingAlertsPath);
      setPendingAlertsPath(null);
    }, 280);

    return () => window.clearTimeout(timer);
  }, [navigate, pendingAlertsPath]);

  const openAlertsWithFeedback = (path: string) => {
    if (pendingAlertsPath) return;
    setPendingAlertsPath(path);
  };

  const { data: summaryData, error: summaryError } = useQuery({
    queryKey: ["summary", timeRange],
    queryFn: () => getSummary(timeRange),
    refetchInterval: pollInterval,
  });

  const { data: timeSeriesData, isLoading: timeSeriesLoading, error: timeSeriesError } = useQuery({
    queryKey: ["alertsOverTime", timeRange],
    queryFn: () => getAlertsOverTime(timeRange === "1h" ? "minute" : "hour", timeRange),
    refetchInterval: pollInterval,
  });

  const { data: distributionData, isLoading: distributionLoading, error: distributionError } = useQuery({
    queryKey: ["distribution", timeRange],
    queryFn: () => getDistribution(timeRange),
    refetchInterval: pollInterval,
  });

  const { data: recentAlertsData, isLoading: recentLoading, error: recentError } = useQuery({
    queryKey: ["recentAlerts", timeRange],
    queryFn: () => getRecentAlerts(15, timeRange),
    refetchInterval: pollInterval,
  });

  const { data: threatMetricsData, isLoading: threatLoading, error: threatError } = useQuery({
    queryKey: ["threatMetrics", timeRange],
    queryFn: () => getThreatMetrics(timeRange, 5),
    refetchInterval: pollInterval,
  });

  const chartData = useMemo(() => timeSeriesData?.data || [], [timeSeriesData?.data]);

  const distributionChartData = useMemo(() => {
    if (!distributionData?.data) return [];

    const normalizedCounts = Object.entries(distributionData.data).reduce(
      (acc, [type, count]) => {
        const normalizedType = normalizeEventType(type);
        acc[normalizedType] = (acc[normalizedType] ?? 0) + count;
        return acc;
      },
      {} as Record<string, number>
    );

    return Object.entries(normalizedCounts).map(([type, count]) => ({
      type,
      name: EVENT_CONFIG[type as EventKey]?.label ?? formatEventLabel(type),
      value: count,
      fill: EVENT_CONFIG[type as EventKey]?.color ?? colors.textMuted,
    }));
  }, [distributionData?.data]);

  const summary = summaryData?.data;
  const threatMetrics = threatMetricsData?.data;
  const threatDistribution = threatMetrics?.distribution ?? {
    LOW: 0,
    MEDIUM: 0,
    HIGH: 0,
    CRITICAL: 0,
  };
  const activeModulesCount = useMemo(() => {
    const modules = systemStatus?.active_modules ?? {};
    return Object.values(modules).filter(Boolean).length;
  }, [systemStatus?.active_modules]);
  const criticalAlerts = threatDistribution.CRITICAL || 0;

  const firstError = summaryError || timeSeriesError || distributionError || recentError;
  const errorMessage = firstError instanceof Error ? firstError.message : "Failed to load analytics data.";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-card border border-border flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-textPrimary">Analytics</h1>
            <p className="text-sm text-textSecondary">Real-time alert trends and event distribution</p>
          </div>
        </div>

        <div className="flex gap-2">
          {(["1h", "6h", "24h"] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                timeRange === range
                  ? "bg-card border-border text-textPrimary"
                  : "bg-surface border-border text-textSecondary hover:text-textPrimary"
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {pendingAlertsPath ? (
        <div className="text-xs text-teal-300 animate-pulse">Loading alert view...</div>
      ) : null}

      {firstError ? (
        <div className="rounded-lg border border-red-500 bg-red-500/10 px-4 py-3 text-sm text-red-400">{errorMessage}</div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
        <SummaryCard title="Total Alerts" value={summary?.total || 0} icon={<AlertTriangle size={18} />} denom={`Last ${timeRange}`} />
        <SummaryCard title="Critical Alerts" value={criticalAlerts} icon={<AlertTriangle size={18} />} />
        <SummaryCard title="Avg Threat Score" value={Math.round(summary?.avg_threat_score || 0)} icon={<Activity size={18} />} />
        <SummaryCard title="Peak Threat" value={summary?.peak_threat_score || 0} icon={<Radar size={18} />} />
        <SummaryCard title="Active Modules" value={activeModulesCount} icon={<BarChart3 size={18} />} />
      </div>

      <div
        role="button"
        tabIndex={0}
        onClick={() => openAlertsWithFeedback("/alerts?sort=timestamp")}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            openAlertsWithFeedback("/alerts?sort=timestamp");
          }
        }}
        className="panel-base rounded-lg p-4 cursor-pointer"
      >
          <h2 className="text-base font-semibold text-textPrimary">Alerts Over Time</h2>
          <p className="text-xs text-textSecondary mb-3">Primary trend chart for decision-making</p>

          {timeSeriesLoading ? (
            <div className="h-80 flex items-center justify-center text-sm text-textSecondary">Loading chart...</div>
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={360}>
              <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis dataKey="time" tick={{ fill: colors.textSecondary, fontSize: 12 }} stroke={colors.border} />
                <YAxis tick={{ fill: colors.textSecondary, fontSize: 12 }} stroke={colors.border} />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke={colors.accent}
                  dot={{ fill: colors.accent, r: 4 }}
                  activeDot={{ r: 6 }}
                  strokeWidth={2}
                  isAnimationActive
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-80 flex items-center justify-center text-sm text-textSecondary">No data available</div>
          )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="panel-base rounded-lg p-4">
          <h2 className="text-base font-semibold text-textPrimary">Event Distribution</h2>
          <p className="text-xs text-textSecondary mb-3">By event type</p>

          {distributionLoading ? (
            <div className="h-64 flex items-center justify-center text-sm text-textSecondary">Loading chart...</div>
          ) : distributionChartData.length > 0 && distributionChartData.some((d) => d.value > 0) ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 items-center">
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                <Pie
                  data={distributionChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                  onClick={(entry) => {
                    if (entry && typeof entry.type === "string") {
                      openAlertsWithFeedback(`/alerts?type=${entry.type}`);
                    }
                  }}
                >
                  {distributionChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
                </PieChart>
              </ResponsiveContainer>

              <div className="space-y-2">
                {distributionChartData.map((entry) => (
                  <button
                    key={entry.type}
                    type="button"
                    onClick={() => openAlertsWithFeedback(`/alerts?type=${entry.type}`)}
                    className="w-full flex items-center justify-between p-2 rounded-lg bg-surface border border-border text-left"
                  >
                    <span className="flex items-center gap-2 text-sm text-textPrimary">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${
                          EVENT_CONFIG[entry.type as EventKey]?.dotClass ?? "bg-textMuted"
                        }`}
                      />
                      {entry.name}
                    </span>
                    <span className="text-xs text-textSecondary">{entry.value}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-sm text-textSecondary">No data available</div>
          )}
        </div>

        <div className="panel-base rounded-lg p-4">
          <h2 className="text-base font-semibold text-textPrimary">Threat Distribution</h2>
          <p className="text-xs text-textSecondary mb-3">Risk spread by severity</p>

          {threatLoading ? (
            <div className="py-8 text-center text-sm text-textSecondary">Loading threat distribution...</div>
          ) : (
            <div className="space-y-3">
              {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const).map((level) => {
                const count = threatDistribution[level] || 0;
                const total = Object.values(threatDistribution).reduce((sum, value) => sum + value, 0);
                const ratio = total > 0 ? (count / total) * 100 : 0;
                const textClass = threatTextClasses[level];
                const fillClass = threatFillClasses[level];

                return (
                  <button
                    key={level}
                    type="button"
                    onClick={() => openAlertsWithFeedback("/alerts?sort=threat_score")}
                    className="w-full text-left space-y-1"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className={`font-semibold ${textClass}`}>{level}</span>
                      <span className="text-textSecondary">{count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-card overflow-hidden border border-border">
                      <div className={`h-full rounded-full transition-all duration-500 ${fillClass}`} style={{ width: `${ratio}%` }} />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="panel-base rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Activity size={18} className="text-textSecondary" />
          <h2 className="text-base font-semibold text-textPrimary">Recent Activity</h2>
        </div>

        {recentLoading ? (
          <div className="py-4 text-center text-sm text-textSecondary">Loading alerts...</div>
        ) : recentAlertsData?.data && recentAlertsData.data.length > 0 ? (
          <div className="space-y-2">
            {recentAlertsData.data.map((alert) => (
              <RecentAlertItem key={alert.id} alert={alert} />
            ))}
          </div>
        ) : (
          <div className="py-8 text-center text-sm text-textSecondary">No recent alerts in this time range</div>
        )}
      </div>
    </div>
  );
}
