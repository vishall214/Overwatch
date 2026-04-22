import { useQuery } from "@tanstack/react-query";
import { fetchCameraStatus } from "../api/camera";
import { getVisibleRefetchInterval, POLLING_INTERVAL_MS } from "./polling";

export function useCameraStatus(enabled = true) {
  return useQuery({
    queryKey: ["cameraStatus"],
    queryFn: fetchCameraStatus,
    enabled,
    refetchInterval: () =>
      enabled ? getVisibleRefetchInterval(POLLING_INTERVAL_MS.cameraStatus) : false,
    refetchOnWindowFocus: true,
  });
}