import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
import { BarChart3, Activity, AlertTriangle } from "lucide-react";
import {
  getAlertsOverTime,
  getDistribution,
  getSummary,
  getRecentAlerts,
  type AlertRecord,
} from "../services/analyticsService";
import { formatEventLabel, normalizeEventType } from "../utils/normalization";

// Color scheme for events
const EVENT_COLORS = {
  intrusion: "#e74c3c",
  loitering: "#f39c12",
  crowd: "#3498db",
  weapon_in_zone: "#e74c3c",
  weapon_detected: "#9b59b6",
  dangerous_object: "#9b59b6",
};

interface SummaryCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  denom?: string;
}

const SummaryCard: React.FC<SummaryCardProps> = ({
  title,
  value,
  icon,
  color,
  denom,
}) => (
  <div className="rounded-2xl glass-panel p-4 border border-[rgba(255,255,255,0.08)]">
    <div className="flex items-start justify-between mb-3">
      <div>
        <p className="text-xs uppercase tracking-wider text-ow-mist/50 font-semibold mb-1">
          {title}
        </p>
        <p className="text-2xl font-bold text-ow-light/90">{value}</p>
        {denom && <p className="text-xs text-ow-mist/40 mt-1">{denom}</p>}
      </div>
      <div
        className="p-2 rounded-lg"
        style={{ backgroundColor: `${color}15`, borderColor: `${color}30` }}
      >
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

const CustomTooltip: React.FC<CustomTooltipProps> = ({
  active,
  payload,
  label,
}) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg bg-ow-bg/80 backdrop-blur border border-ow-mist/20 p-2 shadow-lg">
        <p className="text-xs text-ow-mist/70">{label}</p>
        <p className="text-sm font-semibold text-ow-teal">{payload[0].value}</p>
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
  const color =
    EVENT_COLORS[normalizedType as keyof typeof EVENT_COLORS] ||
    "#ffffff";
  const time = new Date(alert.timestamp);
  const timeStr = time.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-ow-bg/40 border border-[rgba(255,255,255,0.04)] hover:border-[rgba(255,255,255,0.12)] transition-colors">
      <div
        className="w-3 h-3 rounded-full flex-shrink-0"
        style={{ backgroundColor: color }}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-ow-light/80 capitalize">
          {formatEventLabel(normalizedType)}
        </p>
        <p className="text-xs text-ow-mist/50">{alert.zone}</p>
      </div>
      <p className="text-xs text-ow-mist/40 flex-shrink-0">{timeStr}</p>
    </div>
  );
};

export default function Analytics() {
  const [timeRange, setTimeRange] = useState<"1h" | "6h" | "24h">("24h");
  const pollInterval = 5000;

  // Fetch summary metrics
  const { data: summaryData, isLoading: summaryLoading } = useQuery({
    queryKey: ["summary", timeRange],
    queryFn: () => getSummary(timeRange),
    refetchInterval: pollInterval,
  });

  // Fetch alerts over time  
  const { data: timeSeriesData, isLoading: timeSeriesLoading } = useQuery({
    queryKey: ["alertsOverTime", timeRange],
    queryFn: () =>
      getAlertsOverTime(timeRange === "1h" ? "minute" : "hour", timeRange),
    refetchInterval: pollInterval,
  });

  // Fetch distribution
  const { data: distributionData, isLoading: distributionLoading } = useQuery({
    queryKey: ["distribution", timeRange],
    queryFn: () => getDistribution(timeRange),
    refetchInterval: pollInterval,
  });

  // Fetch recent alerts
  const { data: recentAlertsData, isLoading: recentLoading } = useQuery({
    queryKey: ["recentAlerts"],
    queryFn: () => getRecentAlerts(15),
    refetchInterval: pollInterval,
  });

  // Memoize chart data to prevent unnecessary re-renders
  const chartData = useMemo(
    () => timeSeriesData?.data || [],
    [timeSeriesData?.data]
  );

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
      name: formatEventLabel(type),
      value: count,
      fill: EVENT_COLORS[type as keyof typeof EVENT_COLORS] || "#ffffff",
    }));
  }, [distributionData?.data]);

  const summary = summaryData?.data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-ow-teal to-ow-accent flex items-center justify-center">
            <BarChart3 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-ow-light/90">Analytics</h1>
            <p className="text-sm text-ow-mist/50">
              Real-time alert trends and event distribution
            </p>
          </div>
        </div>

        {/* Time range selector */}
        <div className="flex gap-2">
          {(["1h", "6h", "24h"] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                timeRange === range
                  ? "bg-ow-teal/30 border border-ow-teal/50 text-ow-teal/90"
                  : "bg-ow-bg/40 border border-[rgba(255,255,255,0.08)] text-ow-mist/70 hover:border-ow-teal/30"
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <SummaryCard
          title="Total Alerts"
          value={summary?.total || 0}
          icon={<AlertTriangle size={20} className="text-ow-mist/60" />}
          color="#3498db"
          denom="Last 24h"
        />
        <SummaryCard
          title="Intrusions"
          value={summary?.intrusion || 0}
          icon={
            <div
              className="w-5 h-5 rounded"
              style={{ backgroundColor: EVENT_COLORS.intrusion }}
            />
          }
          color={EVENT_COLORS.intrusion}
        />
        <SummaryCard
          title="Loitering"
          value={summary?.loitering || 0}
          icon={
            <div
              className="w-5 h-5 rounded"
              style={{ backgroundColor: EVENT_COLORS.loitering }}
            />
          }
          color={EVENT_COLORS.loitering}
        />
        <SummaryCard
          title="Crowd Events"
          value={summary?.crowd || 0}
          icon={
            <div
              className="w-5 h-5 rounded"
              style={{ backgroundColor: EVENT_COLORS.crowd }}
            />
          }
          color={EVENT_COLORS.crowd}
        />
        <SummaryCard
          title="Weapon Detected"
          value={summary?.weapon_detected || 0}
          icon={
            <div
              className="w-5 h-5 rounded"
              style={{ backgroundColor: EVENT_COLORS.weapon_detected }}
            />
          }
          color={EVENT_COLORS.weapon_detected}
        />
        <SummaryCard
          title="Weapon In Zone"
          value={summary?.weapon_in_zone || 0}
          icon={
            <div
              className="w-5 h-5 rounded"
              style={{ backgroundColor: EVENT_COLORS.weapon_in_zone }}
            />
          }
          color={EVENT_COLORS.weapon_in_zone}
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Line Chart */}
        <div className="lg:col-span-2 rounded-2xl glass-panel p-6 border border-[rgba(255,255,255,0.08)]">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-ow-light/90">
              Alerts Over Time
            </h2>
            <p className="text-xs text-ow-mist/50">
              Trend for selected time range
            </p>
          </div>

          {timeSeriesLoading ? (
            <div className="h-64 flex items-center justify-center">
              <div className="text-center">
                <div className="w-8 h-8 rounded-full border-2 border-ow-mist/20 border-t-ow-teal animate-spin mx-auto mb-2" />
                <p className="text-xs text-ow-mist/50">Loading chart...</p>
              </div>
            </div>
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart
                data={chartData}
                margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="time"
                  tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
                  stroke="rgba(255,255,255,0.1)"
                />
                <YAxis
                  tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }}
                  stroke="rgba(255,255,255,0.1)"
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#52c9a8"
                  dot={{ fill: "#52c9a8", r: 4 }}
                  activeDot={{ r: 6 }}
                  strokeWidth={2}
                  isAnimationActive
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center">
              <p className="text-sm text-ow-mist/50">No data available</p>
            </div>
          )}
        </div>

        {/* Pie Chart */}
        <div className="rounded-2xl glass-panel p-6 border border-[rgba(255,255,255,0.08)]">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-ow-light/90">
              Event Distribution
            </h2>
            <p className="text-xs text-ow-mist/50">By event type</p>
          </div>

          {distributionLoading ? (
            <div className="h-64 flex items-center justify-center">
              <div className="text-center">
                <div className="w-8 h-8 rounded-full border-2 border-ow-mist/20 border-t-ow-teal animate-spin mx-auto mb-2" />
                <p className="text-xs text-ow-mist/50">Loading chart...</p>
              </div>
            </div>
          ) : distributionChartData.length > 0 &&
            distributionChartData.some((d) => d.value > 0) ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={distributionChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                  labelLine={false}
                >
                  {distributionChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center">
              <p className="text-sm text-ow-mist/50">No data available</p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="rounded-2xl glass-panel p-6 border border-[rgba(255,255,255,0.08)]">
        <div className="flex items-center gap-2 mb-4">
          <Activity size={20} className="text-ow-teal/70" />
          <h2 className="text-lg font-bold text-ow-light/90">Recent Activity</h2>
        </div>

        {recentLoading ? (
          <div className="py-4 text-center">
            <div className="w-6 h-6 rounded-full border-2 border-ow-mist/20 border-t-ow-teal animate-spin mx-auto mb-2" />
            <p className="text-xs text-ow-mist/50">Loading alerts...</p>
          </div>
        ) : recentAlertsData?.data && recentAlertsData.data.length > 0 ? (
          <div className="space-y-2">
            {recentAlertsData.data.map((alert) => (
              <RecentAlertItem key={alert.id} alert={alert} />
            ))}
          </div>
        ) : (
          <div className="py-8 text-center">
            <p className="text-sm text-ow-mist/50">
              No recent alerts in this time range
            </p>
          </div>
        )}
      </div>

      {/* Footer note */}
      <div className="rounded-lg bg-ow-teal/5 border border-ow-teal/20 p-3">
        <p className="text-xs text-ow-mist/60">
          <span className="font-semibold text-ow-teal/80">Auto-refresh:</span>{" "}
          Data updates every 5 seconds. All queries use SQL aggregation for
          optimal performance.
        </p>
      </div>
    </div>
  );
}
