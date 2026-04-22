export interface Alert {
  id: number;
  event_type: string;
  timestamp: string;
  track_id: number | null;
  zone: string;
  metadata: Record<string, unknown>;
  snapshot_path: string;
  snapshot_filename?: string;
  snapshot_url?: string;
  threat_score?: number;
  threat_level?: string;
}

export interface AlertListResponse {
  success?: boolean;
  alerts: Alert[];
  data?: Alert[];
  total: number;
}

export interface AlertStats {
  total_alerts: number;
  intrusion: number;
  loitering: number;
  crowd: number;
  face_match: number;
  weapon_detected: number;
  weapon_in_zone: number;
  dangerous_object: number;
}
