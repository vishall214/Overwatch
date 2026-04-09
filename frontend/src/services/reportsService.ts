import { API } from "../api/config";
import { getAuthHeaders } from "../api/auth";

export type ReportPeriod = "daily" | "weekly";

export interface ReportSummary {
  total?: number;
  intrusion?: number;
  loitering?: number;
  crowd?: number;
  weapon_detected?: number;
  weapon_in_zone?: number;
  avg_threat_score?: number;
  peak_threat_score?: number;
}

export interface ReportFiles {
  json: string;
  csv: string;
}

export interface ReportListItem {
  id: string;
  period: ReportPeriod;
  trigger: string;
  generated_at: string;
  summary: ReportSummary;
  files: ReportFiles;
}

export interface ReportEventItem {
  id: number;
  event_type: string;
  zone: string;
  timestamp: string;
  track_id: number | null;
  threat_score: number;
  threat_level: string;
  snapshot_path: string;
  snapshot_filename?: string;
  snapshot_url?: string;
}

export interface ReportPayload {
  report_id: string;
  period: ReportPeriod;
  trigger: string;
  generated_at: string;
  window: {
    start: string;
    end: string;
    hours: number;
  };
  summary: ReportSummary;
  distribution: Record<string, number>;
  threat: {
    distribution: Record<string, number>;
    avg_threat_score: number;
    peak_threat_score: number;
    peak_events: Array<{
      id: number;
      event_type: string;
      zone: string;
      timestamp: string;
      threat_score: number;
      threat_level: string;
    }>;
  };
  trend: Array<{ time: string; count: number }>;
  recent_events: ReportEventItem[];
}

export interface ReportsListResponse {
  success: boolean;
  data: ReportListItem[];
  count: number;
}

export interface ReportDetailsResponse {
  success: boolean;
  data: ReportPayload;
}

export interface GenerateReportResponse {
  success: boolean;
  data: ReportListItem & { email_sent: boolean };
}

export interface SchedulerStatus {
  enabled: boolean;
  running: boolean;
  daily_time_utc: string;
  weekly_day_utc: number;
  poll_seconds: number;
  last_daily_date: string;
  last_weekly_key: string;
  email_enabled: boolean;
  email_recipients_count: number;
}

export interface SchedulerStatusResponse {
  success: boolean;
  data: SchedulerStatus;
}

export async function listReports(limit = 30): Promise<ReportsListResponse> {
  const response = await fetch(API.reports.list(Math.min(Math.max(limit, 1), 200)), {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Failed to fetch reports");
  return response.json();
}

export async function generateReport(period: ReportPeriod): Promise<GenerateReportResponse> {
  const response = await fetch(API.reports.generate(period), {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Failed to generate report");
  return response.json();
}

export async function getReport(reportId: string): Promise<ReportDetailsResponse> {
  const response = await fetch(API.reports.details(reportId), {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Failed to load report details");
  return response.json();
}

export async function getReportSchedulerStatus(): Promise<SchedulerStatusResponse> {
  const response = await fetch(API.reports.scheduler, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Failed to fetch report scheduler status");
  return response.json();
}

export async function downloadReport(
  reportId: string,
  format: "json" | "csv" = "json",
): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API.reports.download(reportId)}?format=${format}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Failed to download report artifact");

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || `${reportId}.${format}`;

  return { blob, filename };
}
