import { useQuery } from "@tanstack/react-query";
import { fetchSystemStatus, fetchSystemMetrics } from "../api/system";

export function useSystemStatus() {
  return useQuery({
    queryKey: ["systemStatus"],
    queryFn: fetchSystemStatus,
    refetchInterval: 2000,
  });
}

export function useSystemMetrics() {
  return useQuery({
    queryKey: ["systemMetrics"],
    queryFn: fetchSystemMetrics,
    refetchInterval: 5000,
  });
}
