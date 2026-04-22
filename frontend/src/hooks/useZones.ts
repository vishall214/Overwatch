import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchZones, createZone, deleteZone } from "../api/zones";
import type { ZoneCreatePayload } from "../api/zones";
import { getVisibleRefetchInterval, POLLING_INTERVAL_MS } from "./polling";

export function useZones(enabled = true) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["zones"],
    queryFn: fetchZones,
    enabled,
    refetchInterval: () =>
      enabled ? getVisibleRefetchInterval(POLLING_INTERVAL_MS.zones) : false,
    refetchOnWindowFocus: true,
  });

  const addMutation = useMutation({
    mutationFn: (payload: ZoneCreatePayload) => createZone(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["zones"] }),
  });

  const removeMutation = useMutation({
    mutationFn: (id: number) => deleteZone(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["zones"] }),
  });

  return {
    zones: query.data?.zones ?? [],
    isLoading: query.isLoading,
    addZone: addMutation.mutate,
    removeZone: removeMutation.mutate,
    refresh: () => queryClient.invalidateQueries({ queryKey: ["zones"] }),
  };
}
