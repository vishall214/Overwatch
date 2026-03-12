export interface ModulesState {
  intrusion: boolean;
  loitering: boolean;
  crowd: boolean;
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
