import { useQuery } from "@tanstack/react-query";
import { fetchAlerts, fetchAlertStats } from "../api/alerts";

export function useAlerts(limit = 100) {
  return useQuery({
    queryKey: ["alerts", limit],
    queryFn: () => fetchAlerts(limit),
    refetchInterval: 5000,
  });
}

export function useAlertStats() {
  return useQuery({
    queryKey: ["alertStats"],
    queryFn: fetchAlertStats,
    refetchInterval: 5000,
  });
}
