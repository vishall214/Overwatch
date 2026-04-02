import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { fetchCameraStatus, startCamera, stopCamera } from "../api/camera";
import { useCameraStatus } from "../hooks/useCameraStatus";
import { LoaderCircle, LogIn, LogOut, Square, User, Video, Wifi, WifiOff } from "lucide-react";
import type { ModulesState, SystemStatus } from "../types/system";

const DEFAULT_MODULES: ModulesState = {
  intrusion: true,
  loitering: true,
  crowd: true,
};

export default function Topbar({ collapsed }: { collapsed: boolean }) {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated, user, logout } = useAuth();
  const { data: status } = useSystemStatus();
  const { data: cameraStatus } = useCameraStatus();
  const [cameraAction, setCameraAction] = useState<"idle" | "starting" | "stopping">("idle");
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraRunningOverride, setCameraRunningOverride] = useState<boolean | null>(null);

  // Hide topbar on landing / login
  if (location.pathname === "/" || location.pathname === "/login" || location.pathname === "/signup") return null;

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  const isDashboard = location.pathname === "/dashboard";
  const cameraOnline = cameraRunningOverride ?? cameraStatus?.is_running ?? status?.camera_running ?? false;
  const isStartingCamera = cameraAction === "starting";
  const isStoppingCamera = cameraAction === "stopping";
  const cameraActionPending = isStartingCamera || isStoppingCamera;

  // Only clear the optimistic override once the *camera status query* has
  // been freshly confirmed — never clear it based on system/status alone,
  // which may lag behind by one poll cycle.
  useEffect(() => {
    if (cameraRunningOverride == null) return;
    if (cameraStatus?.is_running === cameraRunningOverride) {
      setCameraRunningOverride(null);
    }
  }, [cameraRunningOverride, cameraStatus?.is_running]);

  function refreshCameraState(cameraRunning: boolean) {
    setCameraRunningOverride(cameraRunning);
    queryClient.setQueryData<SystemStatus>(["systemStatus"], (current) => ({
      camera_running: cameraRunning,
      pipeline_fps: cameraRunning ? current?.pipeline_fps ?? 0 : 0,
      active_modules: current?.active_modules ?? DEFAULT_MODULES,
      alerts_total: current?.alerts_total ?? 0,
    }));
    queryClient.setQueryData(["cameraStatus"], (current: unknown) => ({
      ...(current && typeof current === "object" ? current as Record<string, unknown> : {}),
      is_running: cameraRunning,
    }));

    void queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
    void queryClient.invalidateQueries({ queryKey: ["systemMetrics"] });
    void queryClient.invalidateQueries({ queryKey: ["cameraStatus"] });
  }

  async function waitForCameraRunning(expectedRunning: boolean, timeoutMs: number) {
    const deadline = Date.now() + timeoutMs;

    while (Date.now() < deadline) {
      try {
        const currentStatus = await fetchCameraStatus();
        const isRunning = currentStatus.is_running ?? false;

        queryClient.setQueryData(["cameraStatus"], currentStatus);

        if (isRunning === expectedRunning) {
          refreshCameraState(expectedRunning);
          return;
        }
      } catch {
        // Transient network error — just retry on the next tick rather than
        // aborting the whole wait. The camera may still be starting up.
        console.warn("Camera status poll failed, retrying...");
      }

      await new Promise((resolve) => window.setTimeout(resolve, 1000));
    }

    throw new Error(expectedRunning ? "Camera start is taking too long" : "Camera stop is taking too long");
  }

  async function handleCameraToggle() {
    if (cameraActionPending) return;

    setCameraError(null);

    try {
      if (cameraOnline) {
        setCameraAction("stopping");
        await stopCamera();
        await waitForCameraRunning(false, 10000);
      } else {
        setCameraAction("starting");
        await startCamera();
        await waitForCameraRunning(true, 30000);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to control camera";
      setCameraError(message);
      void queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
      void queryClient.invalidateQueries({ queryKey: ["systemMetrics"] });
      void queryClient.invalidateQueries({ queryKey: ["cameraStatus"] });
      console.error("Camera control failed", error);
    } finally {
      setCameraAction("idle");
    }
  }

  return (
    <header
      className="fixed top-0 right-0 h-14 z-30 flex items-center justify-between px-6
                 border-b border-[rgba(255,255,255,0.06)] transition-all duration-300"
      style={{
        left: collapsed ? 68 : 220,
        background: "rgba(10,43,54,0.65)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
      }}
    >
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-ow-mist/70 uppercase tracking-wider">
          {location.pathname.replace("/", "") || "Dashboard"}
        </h1>

        {isDashboard ? (
          <button
            type="button"
            onClick={handleCameraToggle}
            disabled={cameraActionPending}
            className={[
              "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide transition-colors",
              isStartingCamera
                ? "border-emerald-400/35 bg-emerald-500/18 text-emerald-300 hover:bg-emerald-500/22"
                : cameraOnline
                ? "border-ow-alert-intrusion/35 bg-ow-alert-intrusion/12 text-ow-alert-intrusion hover:bg-ow-alert-intrusion/18"
                : "border-ow-accent/25 bg-ow-accent/12 text-ow-accent hover:bg-ow-accent/18",
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
        ) : null}

        {isDashboard && cameraError ? (
          <span className="text-[11px] text-ow-alert-intrusion/85">{cameraError}</span>
        ) : null}
      </div>

      <div className="flex items-center gap-4">
        {/* System status indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-ow-accent/5 border border-ow-accent/10">
          {cameraOnline ? (
            <Wifi className="w-3.5 h-3.5 text-ow-accent" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-ow-alert-intrusion" />
          )}
          <span className={`text-xs font-medium ${cameraOnline ? "text-ow-accent" : "text-ow-alert-intrusion"}`}>
            {cameraOnline ? "System Online" : "System Offline"}
          </span>
        </div>

        {/* Auth */}
        {isAuthenticated ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-ow-accent/5 border border-ow-accent/10">
              <User className="w-3.5 h-3.5 text-ow-accent" />
              <span className="text-xs text-ow-light/70">{user}</span>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg hover:bg-ow-accent/5 text-ow-mist/50 hover:text-ow-accent/80 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-ow-accent/10 border border-ow-accent/20
                       text-ow-accent text-xs font-medium hover:bg-ow-accent/20 transition-colors"
          >
            <LogIn className="w-3.5 h-3.5" />
            Sign In
          </Link>
        )}
      </div>
    </header>
  );
}
