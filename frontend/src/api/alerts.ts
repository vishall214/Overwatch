import { API } from "./config";
import type { AlertListResponse, AlertStats } from "../types/alerts";

export async function fetchAlerts(limit = 100): Promise<AlertListResponse> {
  const res = await fetch(`${API.alerts.list}?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
}

export async function fetchAlertStats(): Promise<AlertStats> {
  const res = await fetch(API.alerts.stats);
  if (!res.ok) throw new Error("Failed to fetch alert stats");
  return res.json();
}
