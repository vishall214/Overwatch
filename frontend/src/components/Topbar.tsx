import { useLocation, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { LogIn, LogOut, User, Wifi, WifiOff } from "lucide-react";

export default function Topbar({ collapsed }: { collapsed: boolean }) {
  const location = useLocation();
  const { isAuthenticated, user, logout } = useAuth();
  const { data: status } = useSystemStatus();

  // Hide topbar on landing / login
  if (location.pathname === "/" || location.pathname === "/login") return null;

  const cameraOnline = status?.camera_running ?? false;

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
      {/* Page title */}
      <h1 className="text-sm font-semibold text-ow-mist/70 uppercase tracking-wider">
        {location.pathname.replace("/", "") || "Dashboard"}
      </h1>

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
              onClick={logout}
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
