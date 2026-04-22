import { useQuery } from "@tanstack/react-query";
import { fetchAlerts, fetchAlertStats } from "../api/alerts";
import { getVisibleRefetchInterval, POLLING_INTERVAL_MS } from "./polling";

export function useAlerts(limit = 100, enabled = true) {
  return useQuery({
    queryKey: ["alerts", limit],
    queryFn: () => fetchAlerts(limit),
    enabled,
    refetchInterval: () =>
      enabled ? getVisibleRefetchInterval(POLLING_INTERVAL_MS.alerts) : false,
    refetchOnWindowFocus: true,
  });
}

export function useAlertStats(enabled = true) {
  return useQuery({
    queryKey: ["alertStats"],
    queryFn: fetchAlertStats,
    enabled,
    refetchInterval: () =>
      enabled ? getVisibleRefetchInterval(POLLING_INTERVAL_MS.alertStats) : false,
    refetchOnWindowFocus: true,
  });
}
