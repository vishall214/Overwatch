import { useQuery } from "@tanstack/react-query";
import { fetchSystemStatus, fetchSystemMetrics } from "../api/system";
import { getVisibleRefetchInterval, POLLING_INTERVAL_MS } from "./polling";

export function useSystemStatus(enabled = true) {
  return useQuery({
    queryKey: ["systemStatus"],
    queryFn: fetchSystemStatus,
    enabled,
    refetchInterval: () =>
      enabled ? getVisibleRefetchInterval(POLLING_INTERVAL_MS.systemStatus) : false,
    refetchOnWindowFocus: true,
  });
}

export function useSystemMetrics(enabled = true) {
  return useQuery({
    queryKey: ["systemMetrics"],
    queryFn: fetchSystemMetrics,
    enabled,
    refetchInterval: () =>
      enabled ? getVisibleRefetchInterval(POLLING_INTERVAL_MS.systemMetrics) : false,
    refetchOnWindowFocus: true,
  });
}
