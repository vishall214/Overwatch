import { useQuery } from "@tanstack/react-query";
import { fetchCameraStatus } from "../api/camera";

export function useCameraStatus() {
  return useQuery({
    queryKey: ["cameraStatus"],
    queryFn: fetchCameraStatus,
    refetchInterval: 2000,
  });
}