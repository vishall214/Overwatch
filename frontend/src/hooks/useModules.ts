import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchModules, enableModule, disableModule } from "../api/system";

export function useModules() {
  return useQuery({
    queryKey: ["modules"],
    queryFn: fetchModules,
    refetchInterval: 5000,
  });
}

export function useToggleModule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, enable }: { name: string; enable: boolean }) =>
      enable ? enableModule(name) : disableModule(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["modules"] });
    },
  });
}
