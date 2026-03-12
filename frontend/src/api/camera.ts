import { API } from "./config";
import type { CameraStatus } from "../types/system";

export async function startCamera(source?: string): Promise<{ message: string }> {
  const res = await fetch(API.camera.start, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: source ? JSON.stringify({ source }) : undefined,
  });
  if (!res.ok) throw new Error("Failed to start camera");
  return res.json();
}

export async function stopCamera(): Promise<{ message: string }> {
  const res = await fetch(API.camera.stop, { method: "POST" });
  if (!res.ok) throw new Error("Failed to stop camera");
  return res.json();
}

export async function fetchCameraStatus(): Promise<CameraStatus> {
  const res = await fetch(API.camera.status);
  if (!res.ok) throw new Error("Failed to fetch camera status");
  return res.json();
}
