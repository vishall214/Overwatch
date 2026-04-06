import { API } from "./config";

export interface Zone {
  id: number;
  name: string | null;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  camera_id: string;
  is_active: boolean;
  created_at: string;
}

export interface ZoneListResponse {
  zones: Zone[];
  total: number;
}

export interface ZoneCreatePayload {
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  name?: string;
  camera_id?: string;
}

export async function fetchZones(): Promise<ZoneListResponse> {
  const res = await fetch(API.zones.list);
  if (!res.ok) throw new Error("Failed to fetch zones");
  return res.json();
}

export async function createZone(payload: ZoneCreatePayload): Promise<Zone> {
  console.log("ZONE API PAYLOAD:", payload);
  const res = await fetch(API.zones.create, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create zone");
  const created = await res.json();
  console.log("ZONE API RESPONSE:", created);
  return created;
}

export async function deleteZone(id: number): Promise<void> {
  const res = await fetch(API.zones.delete(id), { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete zone");
}
