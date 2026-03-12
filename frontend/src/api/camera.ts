import { API } from "./config";
import type { CameraStatus } from "../types/system";

async function readErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json() as { detail?: string; message?: string };
    return data.detail ?? data.message ?? fallback;
  } catch {
    return fallback;
  }
}

export async function startCamera(source?: string): Promise<{ message: string }> {
  const body = source != null ? JSON.stringify({ source }) : undefined;
  const res = await fetch(API.camera.start, {
    method: "POST",
    headers: body != null ? { "Content-Type": "application/json" } : undefined,
    body,
  });

  // 409 means the pipeline is already running — treat as success so the
  // frontend can confirm running state via the status poll without erroring.
  if (res.status === 409) {
    return { message: "Pipeline already running" };
  }

  if (!res.ok) throw new Error(await readErrorMessage(res, "Failed to start camera"));
  return res.json();
}

export async function stopCamera(): Promise<{ message: string }> {
  const res = await fetch(API.camera.stop, { method: "POST" });
  if (!res.ok) throw new Error(await readErrorMessage(res, "Failed to stop camera"));
  return res.json();
}

export async function fetchCameraStatus(): Promise<CameraStatus> {
  const res = await fetch(API.camera.status);
  if (!res.ok) throw new Error("Failed to fetch camera status");
  return res.json();
}
