const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export const API = {
  auth: {
    signup: `${API_BASE}/auth/signup`,
    login: `${API_BASE}/auth/login`,
  },
  camera: {
    stream: `${API_BASE}/camera/stream`,
    start: `${API_BASE}/camera/start`,
    stop: `${API_BASE}/camera/stop`,
    status: `${API_BASE}/camera/status`,
  },
  video: {
    source: `${API_BASE}/video/source`,
    demoList: (category: string) => `${API_BASE}/video/demo/list?category=${encodeURIComponent(category)}`,
    upload: `${API_BASE}/video/upload`,
    deleteUpload: (filename: string) => `${API_BASE}/video/upload/${encodeURIComponent(filename)}`,
    sourceInfo: `${API_BASE}/video/source/info`,
  },
  analytics: {
    alertsOverTime: (interval: string, range: string) =>
      `${API_BASE}/analytics/alerts-over-time?interval=${interval}&range_=${range}`,
    distribution: (range: string) => `${API_BASE}/analytics/distribution?range_=${range}`,
    summary: (range: string) => `${API_BASE}/analytics/summary?range_=${range}`,
    recent: (limit: number) => `${API_BASE}/analytics/recent?limit=${limit}`,
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
