import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  ShieldAlert,
  Eye,
  Users,
  Bell,
  BarChart3,
  Home,
  PanelLeftClose,
  PanelLeft,
  Crosshair,
} from "lucide-react";

const links = [
  { to: "/", label: "Landing", icon: Home },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/intrusion", label: "Intrusion", icon: ShieldAlert },
  { to: "/loitering", label: "Loitering", icon: Eye },
  { to: "/crowd", label: "Crowd", icon: Users },
  { to: "/weapons", label: "Weapons", icon: Crosshair },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
];

export default function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const location = useLocation();

  // Hide sidebar on landing page and login
  if (location.pathname === "/" || location.pathname === "/login" || location.pathname === "/signup") return null;

  return (
    <aside
      className={`fixed left-0 top-0 h-screen z-40 flex flex-col transition-all duration-300 ease-in-out
                  border-r border-[rgba(255,255,255,0.08)]
                  ${collapsed ? "w-[68px]" : "w-[220px]"}`}
      style={{ background: "rgba(10,43,54,0.85)", backdropFilter: "blur(18px)", WebkitBackdropFilter: "blur(18px)" }}
    >
      {/* Brand */}
      <div className={`flex items-center border-b border-[rgba(255,255,255,0.06)] ${collapsed ? "px-3 py-5 justify-center" : "px-5 py-5"}`}>
        <NavLink to="/" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-ow-accent to-ow-accent-dim flex items-center justify-center flex-shrink-0 shadow-glow">
            <Eye className="w-4.5 h-4.5 text-ow-bg" />
          </div>
          {!collapsed && (
            <span className="text-[15px] font-bold tracking-widest text-ow-accent">
              OVERWATCH
            </span>
          )}
        </NavLink>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {links.slice(1).map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            title={collapsed ? link.label : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl text-sm font-medium transition-all duration-200
               ${collapsed ? "px-3 py-2.5 justify-center" : "px-3 py-2.5"}
               ${isActive
                ? "bg-ow-accent/10 text-ow-accent border border-ow-accent/15 shadow-glow"
                : "text-ow-mist hover:text-ow-accent/80 hover:bg-ow-accent/5 border border-transparent"
              }`
            }
          >
            <link.icon className="w-[18px] h-[18px] flex-shrink-0" />
            {!collapsed && <span>{link.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="px-2 py-3 border-t border-[rgba(255,255,255,0.06)]">
        <button
          onClick={onToggle}
          className={`flex items-center gap-2 w-full rounded-xl py-2 text-ow-mist/60 hover:text-ow-accent/70 hover:bg-ow-accent/5
                     transition-all duration-200 ${collapsed ? "justify-center px-2" : "px-3"}`}
        >
          {collapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
          {!collapsed && <span className="text-xs">Collapse</span>}
        </button>
      </div>

      {/* Footer */}
      {!collapsed && (
        <div className="px-5 py-3 border-t border-[rgba(255,255,255,0.04)]">
          <p className="text-[10px] text-ow-mist/30 font-mono tracking-wider">OVERWATCH v2.0</p>
        </div>
      )}
    </aside>
  );
}
