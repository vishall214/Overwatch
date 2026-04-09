import { API } from "../api/config";
import { getAuthHeaders, invalidateAuthSession } from "../api/auth";

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
  avg_threat_score: number;
  peak_threat_score: number;
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
  snapshot_filename?: string;
  snapshot_url?: string;
  threat_score: number;
  threat_level: string;
}

export interface RecentAlertsResponse {
  success: boolean;
  data: AlertRecord[];
  count: number;
  range?: string;
}

export interface ThreatDistribution {
  LOW: number;
  MEDIUM: number;
  HIGH: number;
  CRITICAL: number;
}

export interface ThreatPeakEvent {
  id: number;
  event_type: string;
  zone: string;
  timestamp: string;
  threat_score: number;
  threat_level: string;
}

export interface ThreatMetrics {
  distribution: ThreatDistribution;
  avg_threat_score: number;
  peak_threat_score: number;
  peak_events: ThreatPeakEvent[];
}

export interface ThreatMetricsResponse {
  success: boolean;
  data: ThreatMetrics;
  range: string;
}

async function parseErrorMessage(res: Response, fallback: string): Promise<string> {
  let detailMessage = "";

  try {
    const payload = await res.json();
    if (payload && typeof payload.detail === "string" && payload.detail.trim()) {
      detailMessage = payload.detail.trim();
    }
  } catch {
    // Ignore JSON parse errors and fall back to a generic message.
  }

  const normalizedDetail = detailMessage.toLowerCase();
  const isAuthDetail = normalizedDetail.includes("invalid token") || normalizedDetail.includes("not authenticated");

  if (res.status === 401 || res.status === 403 || isAuthDetail) {
    invalidateAuthSession();
    return "Session expired. Please sign in again.";
  }

  if (detailMessage) {
    return detailMessage;
  }

  return fallback;
}

/**
 * Get alert counts over time with specified interval and range.
 */
export async function getAlertsOverTime(
  interval: "minute" | "hour" = "minute",
  range: "1h" | "6h" | "24h" = "1h"
): Promise<AlertsOverTimeResponse> {
  const res = await fetch(API.analytics.alertsOverTime(interval, range), { headers: getAuthHeaders() });
  if (!res.ok) {
    const message = await parseErrorMessage(res, "Failed to fetch alerts over time");
    throw new Error(message);
  }
  return res.json();
}

/**
 * Get event distribution for the specified time range.
 */
export async function getDistribution(
  range: "1h" | "6h" | "24h" = "24h"
): Promise<DistributionResponse> {
  const res = await fetch(API.analytics.distribution(range), {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const message = await parseErrorMessage(res, "Failed to fetch distribution");
    throw new Error(message);
  }
  return res.json();
}

/**
 * Get summary metrics for the specified time range.
 */
export async function getSummary(
  range: "1h" | "6h" | "24h" = "24h"
): Promise<SummaryResponse> {
  const res = await fetch(API.analytics.summary(range), {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const message = await parseErrorMessage(res, "Failed to fetch summary");
    throw new Error(message);
  }
  return res.json();
}

/**
 * Get recent alerts for the activity feed.
 */
export async function getRecentAlerts(
  limit: number = 20,
  range: "1h" | "6h" | "24h" = "24h",
): Promise<RecentAlertsResponse> {
  const res = await fetch(API.analytics.recent(Math.min(limit, 100), range), {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const message = await parseErrorMessage(res, "Failed to fetch recent alerts");
    throw new Error(message);
  }
  return res.json();
}

/**
 * Get threat distribution, averages, and peak events.
 */
export async function getThreatMetrics(
  range: "1h" | "6h" | "24h" = "24h",
  limit: number = 5,
): Promise<ThreatMetricsResponse> {
  const safeLimit = Math.min(Math.max(limit, 1), 50);
  const res = await fetch(API.analytics.threat(range, safeLimit), { headers: getAuthHeaders() });
  if (!res.ok) {
    // Older backends may not expose the threat endpoint yet.
    if (res.status === 404) {
      return {
        success: true,
        range,
        data: {
          distribution: {
            LOW: 0,
            MEDIUM: 0,
            HIGH: 0,
            CRITICAL: 0,
          },
          avg_threat_score: 0,
          peak_threat_score: 0,
          peak_events: [],
        },
      };
    }
    const message = await parseErrorMessage(res, "Failed to fetch threat metrics");
    throw new Error(message);
  }
  return res.json();
}
