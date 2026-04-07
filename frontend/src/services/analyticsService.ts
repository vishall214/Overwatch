import { API } from "../api/config";
import { getAuthHeaders } from "../api/auth";

export interface TimeSeriesPoint {
  time: string;
  count: number;
}

export interface AlertsOverTimeResponse {
  success: boolean;
  data: TimeSeriesPoint[];
  interval: string;
  range: string;
}

export interface EventDistribution {
  intrusion: number;
  loitering: number;
  crowd: number;
  weapon_detected: number;
  weapon_in_zone: number;
  dangerous_object: number;
}

export interface DistributionResponse {
  success: boolean;
  data: EventDistribution;
  range: string;
}

export interface SummaryMetrics {
  total: number;
  intrusion: number;
  loitering: number;
  crowd: number;
  weapon_detected: number;
  weapon_in_zone: number;
  dangerous_object: number;
  face_match: number;
}

export interface SummaryResponse {
  success: boolean;
  data: SummaryMetrics;
  range: string;
}

export interface AlertRecord {
  id: number;
  event_type: string;
  zone: string;
  timestamp: string;
  track_id: number | null;
  snapshot_path: string;
}

export interface RecentAlertsResponse {
  success: boolean;
  data: AlertRecord[];
  count: number;
}

const ANALYTICS_BASE = API.camera.stream.replace("/stream", "");

/**
 * Get alert counts over time with specified interval and range.
 */
export async function getAlertsOverTime(
  interval: "minute" | "hour" = "minute",
  range: "1h" | "6h" | "24h" = "1h"
): Promise<AlertsOverTimeResponse> {
  const res = await fetch(
    `${ANALYTICS_BASE}/analytics/alerts-over-time?interval=${interval}&range_=${range}`,
    { headers: getAuthHeaders() }
  );
  if (!res.ok) throw new Error("Failed to fetch alerts over time");
  return res.json();
}

/**
 * Get event distribution for the specified time range.
 */
export async function getDistribution(
  range: "1h" | "6h" | "24h" = "24h"
): Promise<DistributionResponse> {
  const res = await fetch(`${ANALYTICS_BASE}/analytics/distribution?range_=${range}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch distribution");
  return res.json();
}

/**
 * Get summary metrics for the specified time range.
 */
export async function getSummary(
  range: "1h" | "6h" | "24h" = "24h"
): Promise<SummaryResponse> {
  const res = await fetch(`${ANALYTICS_BASE}/analytics/summary?range_=${range}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch summary");
  return res.json();
}

/**
 * Get recent alerts for the activity feed.
 */
export async function getRecentAlerts(limit: number = 20): Promise<RecentAlertsResponse> {
  const res = await fetch(`${ANALYTICS_BASE}/analytics/recent?limit=${Math.min(limit, 100)}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch recent alerts");
  return res.json();
}
