import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { LoaderCircle, LogIn, LogOut, Square, User, UserPlus, Video, Wifi, WifiOff } from "lucide-react";
import { startCamera, stopCamera } from "../api/camera";
import { useAuth } from "../context/AuthContext";
import { useCameraStatus } from "../hooks/useCameraStatus";
import { useSystemStatus } from "../hooks/useSystemStatus";

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

export default function Topbar({ collapsed }: { collapsed: boolean }) {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated, user, logout } = useAuth();
  const { data: status } = useSystemStatus();
  const { data: cameraStatus } = useCameraStatus();

  const [cameraAction, setCameraAction] = useState<"idle" | "starting" | "stopping">("idle");
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraRunning, setCameraRunning] = useState<boolean | null>(null);

  const routeTitle =
    ROUTE_TITLES[location.pathname] ??
    (location.pathname.replace("/", "") || "monitor").replace(/(^|[-_])\w/g, (match) => match.toUpperCase());

  const cameraOnline = cameraRunning ?? cameraStatus?.is_running ?? status?.camera_running ?? false;
  const cameraBusy = cameraAction !== "idle";

  useEffect(() => {
    if (cameraRunning == null) return;
    if (cameraStatus?.is_running === cameraRunning) {
      setCameraRunning(null);
    }
  }, [cameraRunning, cameraStatus?.is_running]);

  const invalidateCameraState = () => {
    void queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
    void queryClient.invalidateQueries({ queryKey: ["systemMetrics"] });
    void queryClient.invalidateQueries({ queryKey: ["cameraStatus"] });
  };

  const handleCameraToggle = async () => {
    if (cameraBusy) return;

    const nextRunning = !cameraOnline;
    setCameraError(null);
    setCameraAction(nextRunning ? "starting" : "stopping");

    try {
      if (nextRunning) {
        await startCamera();
      } else {
        await stopCamera();
      }
      setCameraRunning(nextRunning);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to control camera";
      setCameraError(message);
      console.error("Camera control failed", error);
    } finally {
      invalidateCameraState();
      setCameraAction("idle");
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header
      className="fixed right-0 top-0 z-30 flex h-14 items-center justify-between px-4 page-transition"
      style={{ left: collapsed ? 72 : 226 }}
    >
      <div className="glass-card flex h-full w-full items-center justify-between px-4">
        <div className="flex min-w-0 items-center gap-4">
          <h1 className="truncate text-sm font-semibold tracking-wide text-textPrimary sm:text-base">{routeTitle}</h1>

          <button
            type="button"
            onClick={handleCameraToggle}
            disabled={cameraBusy}
            className={`inline-flex items-center gap-1.5 glass-card px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 ${
              cameraOnline ? "text-threat-critical" : "text-accentCyan"
            } ${cameraBusy ? "cursor-not-allowed opacity-70" : "hover:scale-[1.02]"}`}
          >
            {cameraBusy ? (
              <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
            ) : cameraOnline ? (
              <Square className="h-3.5 w-3.5" />
            ) : (
              <Video className="h-3.5 w-3.5" />
            )}
            {cameraAction === "starting"
              ? "Starting Camera"
              : cameraAction === "stopping"
              ? "Stopping Camera"
              : cameraOnline
              ? "Stop Camera"
              : "Start Camera"}
          </button>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold border ${
              cameraOnline
                ? "bg-threat-low/20 border-threat-low/40 text-threat-low"
                : "bg-threat-critical/20 border-threat-critical/40 text-threat-critical"
            }`}
          >
            {cameraOnline ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
            {cameraOnline ? "Online" : "Offline"}
          </span>

          {isAuthenticated ? (
            <>
              <span className="hidden items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 text-[11px] text-textSecondary lg:inline-flex">
                <User className="h-3.5 w-3.5" />
                {user}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-lg p-2 text-textSecondary page-transition hover:scale-[1.02] hover:bg-white/10 hover:text-textPrimary"
                aria-label="Logout"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </>
          ) : (
            <div className="flex items-center gap-1.5">
              <Link to="/login" className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-accentCyan page-transition hover:scale-[1.02] hover:bg-white/10">
                <LogIn className="h-3.5 w-3.5" />
                Sign In
              </Link>
              <Link to="/signup" className="inline-flex items-center gap-1.5 rounded-lg border border-accent/40 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-textPrimary page-transition hover:scale-[1.02] hover:bg-accent/25">
                <UserPlus className="h-3.5 w-3.5" />
                Sign Up
              </Link>
            </div>
          )}
        </div>
      </div>

      {cameraError ? (
        <div className="absolute right-4 top-[58px] rounded-lg bg-threat-critical/20 border border-threat-critical/40 px-3 py-1.5 text-xs text-threat-critical">
          {cameraError}
        </div>
      ) : null}
    </header>
  );
}
