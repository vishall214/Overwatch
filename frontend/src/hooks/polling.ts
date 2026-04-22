const parsePositiveInterval = (raw: unknown, fallback: number): number => {
  const value = Number(raw);
  if (!Number.isFinite(value) || value <= 0) {
    return fallback;
  }
  return Math.floor(value);
};

export const POLLING_INTERVAL_MS = {
  alerts: parsePositiveInterval(import.meta.env.VITE_POLL_ALERTS_MS, 6000),
  alertStats: parsePositiveInterval(import.meta.env.VITE_POLL_ALERT_STATS_MS, 6000),
  systemStatus: parsePositiveInterval(import.meta.env.VITE_POLL_SYSTEM_STATUS_MS, 2500),
  systemMetrics: parsePositiveInterval(import.meta.env.VITE_POLL_SYSTEM_METRICS_MS, 6500),
  cameraStatus: parsePositiveInterval(import.meta.env.VITE_POLL_CAMERA_STATUS_MS, 2500),
  zones: parsePositiveInterval(import.meta.env.VITE_POLL_ZONES_MS, 12000),
} as const;

export const getVisibleRefetchInterval = (intervalMs: number): number | false => {
  if (typeof document !== "undefined" && document.visibilityState !== "visible") {
    return false;
  }
  return intervalMs;
};
