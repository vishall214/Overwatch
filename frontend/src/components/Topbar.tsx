import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { startCamera, stopCamera } from "../api/camera";
import { getSourceInfo } from "../api/video";
import { useCameraStatus } from "../hooks/useCameraStatus";
import { LoaderCircle, LogIn, LogOut, Radar, Square, User, Video, Wifi, WifiOff } from "lucide-react";

const ROUTE_TITLES: Record<string, string> = {
  "/monitor": "Monitor",
  "/alerts": "Alerts",
  "/analytics": "Analytics",
  "/reports": "Reports",
  "/intrusion": "Intrusion",
  "/loitering": "Loitering",
  "/crowd": "Crowd",
  "/weapons": "Weapons",
};

const MODULE_LABELS: Record<string, string> = {
  intrusion: "Intrusion",
  loitering: "Loitering",
  crowd: "Crowd",
  weapon_detection: "Weapons",
};

const SOURCE_LABELS: Record<string, string> = {
  camera: "Live",
  demo: "Demo",
  upload: "Upload",
};

function normalizeModuleParam(value: string | null): string | null {
  if (!value) return null;
  if (value === "weapons") return "weapon_detection";
  if (value === "weapon_detection") return "weapon_detection";
  if (value === "intrusion" || value === "loitering" || value === "crowd") return value;
  return null;
}

export default function Topbar({ collapsed }: { collapsed: boolean }) {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated, user, logout } = useAuth();
  const { data: status } = useSystemStatus();
  const { data: cameraStatus } = useCameraStatus();
  const { data: sourceInfo } = useQuery({
    queryKey: ["sourceInfo"],
    queryFn: getSourceInfo,
    refetchInterval: 2000,
  });
  const [cameraAction, setCameraAction] = useState<"idle" | "starting" | "stopping">("idle");
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraRunning, setCameraRunning] = useState<boolean | null>(null);

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  const cameraOnline = cameraRunning ?? cameraStatus?.is_running ?? status?.camera_running ?? false;
  const isStartingCamera = cameraAction === "starting";
  const isStoppingCamera = cameraAction === "stopping";
  const cameraActionPending = isStartingCamera || isStoppingCamera;

  const routeTitle =
    ROUTE_TITLES[location.pathname] ??
    (location.pathname.replace("/", "") || "monitor").replace(/(^|[-_])\w/g, (m) => m.toUpperCase());
  const requestedModule = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return normalizeModuleParam(params.get("module"));
  }, [location.search]);
  const sourceModule = (sourceInfo as { active_module?: string } | undefined)?.active_module;
  const activeModule = sourceModule ?? requestedModule;
  const activeModuleLabel = activeModule ? MODULE_LABELS[activeModule] ?? activeModule : "None";
  const sourceType = (sourceInfo as { source_type?: string } | undefined)?.source_type;
  const sourceTypeLabel = sourceType ? SOURCE_LABELS[sourceType] ?? sourceType : "Unknown";

  useEffect(() => {
    if (cameraRunning == null) return;
    if (cameraStatus?.is_running === cameraRunning) {
      setCameraRunning(null);
    }
  }, [cameraRunning, cameraStatus?.is_running]);

  function invalidateCameraStream() {
    void queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
    void queryClient.invalidateQueries({ queryKey: ["systemMetrics"] });
    void queryClient.invalidateQueries({ queryKey: ["cameraStatus"] });
  }

  async function handleStartCamera() {
    if (cameraActionPending) return;

    setCameraAction("starting");
    setCameraError(null);

    try {
      await startCamera();
      setCameraRunning(true);
      invalidateCameraStream();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to control camera";
      setCameraError(message);
      invalidateCameraStream();
      console.error("Camera control failed", error);
    } finally {
      setCameraAction("idle");
    }
  }

  async function handleStopCamera() {
    if (cameraActionPending) return;

    setCameraAction("stopping");
    setCameraError(null);

    try {
      await stopCamera();
      setCameraRunning(false);
      invalidateCameraStream();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to control camera";
      setCameraError(message);
      invalidateCameraStream();
      console.error("Camera control failed", error);
    } finally {
      setCameraAction("idle");
    }
  }

  async function handleCameraToggle() {
    if (cameraActionPending) return;
    if (cameraOnline) {
      await handleStopCamera();
      return;
    }
    await handleStartCamera();
  }

  return (
    <header
      className="fixed top-0 right-0 h-14 z-30 flex items-center justify-between px-6
                 glass transition-all duration-300"
      style={{
        left: collapsed ? 68 : 220,
      }}
    >
      <div className="flex items-center gap-3 min-w-0">
        <h1 className="text-base font-semibold text-textPrimary capitalize">
          {routeTitle}
        </h1>

        <button
          type="button"
          onClick={handleCameraToggle}
          disabled={cameraActionPending}
          className={[
            "inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-wide transition-colors",
            isStartingCamera
              ? "bg-accent/30 text-accent"
              : cameraOnline
              ? "bg-threat-critical/10 text-threat-critical"
              : "bg-accent/20 hover:bg-accent/30 text-accent",
            cameraActionPending ? "cursor-not-allowed opacity-70" : "",
          ].join(" ")}
        >
          {cameraActionPending ? (
            <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
          ) : cameraOnline ? (
            <Square className="h-3.5 w-3.5" />
          ) : (
            <Video className="h-3.5 w-3.5" />
          )}
          <span>
            {isStartingCamera ? "Starting..." : isStoppingCamera ? "Stopping..." : cameraOnline ? "Stop Camera" : "Start Camera"}
          </span>
        </button>

        {cameraError ? <span className="text-xs text-threat-critical">{cameraError}</span> : null}
      </div>

      <div className="flex items-center gap-2">
        <div className="glass flex items-center gap-2 px-3 py-1.5 rounded-full">
          <Video className="w-3.5 h-3.5 text-accent" />
          <span className="text-xs text-textSecondary">Source: {sourceTypeLabel}</span>
        </div>

        <div className="glass flex items-center gap-2 px-3 py-1.5 rounded-full">
          <Radar className="w-3.5 h-3.5 text-accent" />
          <span className="text-xs text-textSecondary">Module: {activeModuleLabel}</span>
        </div>

        {/* System status indicator */}
        <div className="glass flex items-center gap-2 px-3 py-1.5 rounded-full">
          {cameraOnline ? (
            <Wifi className="w-3.5 h-3.5 text-accent" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-threat-critical" />
          )}
          <span className={`text-xs font-medium ${cameraOnline ? "text-accent" : "text-threat-critical"}`}>
            {cameraOnline ? "System Online" : "System Offline"}
          </span>
        </div>

        {/* Auth */}
        {isAuthenticated ? (
          <div className="flex items-center gap-3">
            <div className="glass flex items-center gap-2 px-3 py-1.5 rounded-full">
              <User className="w-3.5 h-3.5 text-accent" />
              <span className="text-xs text-textSecondary">{user}</span>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg hover:bg-surface text-textSecondary hover:text-textPrimary transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            className="glass flex items-center gap-2 px-3 py-1.5 rounded-full
                       text-accent text-xs font-medium hover:bg-surface transition-colors"
          >
            <LogIn className="w-3.5 h-3.5" />
            Sign In
          </Link>
        )}
      </div>
    </header>
  );
}
