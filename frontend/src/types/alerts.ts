export interface Alert {
  id: number;
  event_type: string;
  timestamp: string;
  track_id: number | null;
  zone: string;
  metadata: Record<string, unknown>;
  snapshot_path: string;
}

export interface AlertListResponse {
  alerts: Alert[];
  total: number;
}

export interface AlertStats {
  total_alerts: number;
  intrusion: number;
  loitering: number;
  crowd: number;
  face_match: number;
}
