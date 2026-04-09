export interface ModulesState {
  intrusion: boolean;
  loitering: boolean;
  crowd: boolean;
  weapon_detection: boolean;
}

export interface SystemStatus {
  camera_running: boolean;
  pipeline_fps: number;
  active_modules: ModulesState;
  alerts_total: number;
}

export interface StageMetrics {
  items_processed?: number;
  processing_time_avg?: number;
  frames_captured?: number;
  frames_processed?: number;
  frames_tracked?: number;
  frames_analyzed?: number;
  frames_encoded?: number;
  avg_capture_ms?: number;
  avg_inference_ms?: number;
  avg_tracking_ms?: number;
  avg_behavior_ms?: number;
  avg_stream_ms?: number;
  [key: string]: unknown;
}

export interface SystemMetrics {
  capture: StageMetrics;
  inference: StageMetrics;
  tracking: StageMetrics;
  behavior: StageMetrics;
  stream: StageMetrics;
  queues: Record<string, number>;
}

export interface CameraStatus {
  is_running: boolean;
  [key: string]: unknown;
}
