const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export const API = {
  camera: {
    stream: `${API_BASE}/camera/stream`,
    start: `${API_BASE}/camera/start`,
    stop: `${API_BASE}/camera/stop`,
    status: `${API_BASE}/camera/status`,
  },
  alerts: {
    list: `${API_BASE}/alerts`,
    stats: `${API_BASE}/system/alerts/stats`,
  },
  system: {
    modules: `${API_BASE}/system/modules`,
    moduleEnable: (name: string) => `${API_BASE}/system/modules/${encodeURIComponent(name)}/enable`,
    moduleDisable: (name: string) => `${API_BASE}/system/modules/${encodeURIComponent(name)}/disable`,
    status: `${API_BASE}/system/status`,
    metrics: `${API_BASE}/system/metrics`,
  },
  snapshots: (filename: string) => `${API_BASE}/snapshots/${encodeURIComponent(filename)}`,
  upload: `${API_BASE}/upload-video`,
  zones: {
    list: `${API_BASE}/zones`,
    create: `${API_BASE}/zones`,
    delete: (id: number) => `${API_BASE}/zones/${id}`,
  },
} as const;
