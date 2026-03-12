import { API } from "./config";
import type { ModulesState, SystemStatus, SystemMetrics } from "../types/system";

export async function fetchModules(): Promise<ModulesState> {
  const res = await fetch(API.system.modules);
  if (!res.ok) throw new Error("Failed to fetch modules");
  return res.json();
}

export async function enableModule(name: string): Promise<{ module: string; enabled: boolean; modules: ModulesState }> {
  const res = await fetch(API.system.moduleEnable(name), { method: "POST" });
  if (!res.ok) throw new Error(`Failed to enable ${name}`);
  return res.json();
}

export async function disableModule(name: string): Promise<{ module: string; enabled: boolean; modules: ModulesState }> {
  const res = await fetch(API.system.moduleDisable(name), { method: "POST" });
  if (!res.ok) throw new Error(`Failed to disable ${name}`);
  return res.json();
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(API.system.status);
  if (!res.ok) throw new Error("Failed to fetch system status");
  return res.json();
}

export async function fetchSystemMetrics(): Promise<SystemMetrics> {
  const res = await fetch(API.system.metrics);
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}
