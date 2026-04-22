import { API } from "./config";
import { getAuthHeaders } from "./auth";

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
  const res = await fetch(API.zones.create, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create zone");
  return res.json();
}

export async function deleteZone(id: number): Promise<void> {
  const res = await fetch(API.zones.delete(id), {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete zone");
}
