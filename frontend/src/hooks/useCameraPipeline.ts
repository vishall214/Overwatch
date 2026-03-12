import { useMutation, useQueryClient } from "@tanstack/react-query";
import { startCamera, stopCamera } from "../api/camera";
import type { SystemStatus } from "../types/system";

function syncCameraState(queryClient: ReturnType<typeof useQueryClient>, cameraRunning: boolean) {
  queryClient.setQueryData<SystemStatus | undefined>(["systemStatus"], (current) => {
    if (!current) return current;

    return {
      ...current,
      camera_running: cameraRunning,
      pipeline_fps: cameraRunning ? current.pipeline_fps : 0,
    };
  });

  queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
  queryClient.invalidateQueries({ queryKey: ["systemMetrics"] });
}

function reconcileConflictState(queryClient: ReturnType<typeof useQueryClient>, error: Error | null, intendedRunningState: boolean) {
  const message = error?.message.toLowerCase() ?? "";

  if (message.includes("already running")) {
    syncCameraState(queryClient, true);
    return;
  }

  if (message.includes("not running")) {
    syncCameraState(queryClient, false);
    return;
  }

  queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
  queryClient.invalidateQueries({ queryKey: ["systemMetrics"] });

  if (intendedRunningState) return;
}

export function useStartCamera() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (source?: string) => startCamera(source),
    onSuccess: () => {
      syncCameraState(queryClient, true);
    },
    onError: (error) => {
      reconcileConflictState(queryClient, error, true);
    },
  });
}

export function useStopCamera() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: stopCamera,
    onSuccess: () => {
      syncCameraState(queryClient, false);
    },
    onError: (error) => {
      reconcileConflictState(queryClient, error, false);
    },
  });
}