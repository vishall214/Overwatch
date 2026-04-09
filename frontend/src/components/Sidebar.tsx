import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Eye,
  Bell,
  BarChart3,
  FileText,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";

const links = [
  { to: "/monitor", label: "Monitor", icon: LayoutDashboard },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/reports", label: "Reports", icon: FileText },
];

export default function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <aside
      className={`fixed left-0 top-0 h-screen z-40 flex flex-col transition-all duration-300 ease-in-out
                  glass shadow-[inset_0_0_20px_rgba(36,158,148,0.05)]
                  ${collapsed ? "w-[68px]" : "w-[220px]"}`}
    >
      {/* Brand */}
      <div className={`flex items-center ${collapsed ? "px-3 py-5 justify-center" : "px-5 py-5"}`}>
        <NavLink to="/" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.1)] flex items-center justify-center flex-shrink-0">
            <Eye className="w-4.5 h-4.5 text-accent" />
          </div>
          {!collapsed && (
            <span className="text-base font-semibold text-textPrimary">
              OVERWATCH
            </span>
          )}
        </NavLink>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            title={collapsed ? link.label : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg text-sm font-medium transition-all duration-200
               ${collapsed ? "px-3 py-2.5 justify-center" : "px-3 py-2.5"}
               ${isActive
                ? "bg-[rgba(36,158,148,0.15)] text-textPrimary border border-[rgba(36,158,148,0.4)] shadow-[0_0_10px_rgba(36,158,148,0.2)]"
                : "text-textSecondary hover:text-textPrimary hover:bg-[rgba(255,255,255,0.06)] border border-transparent"
              }`
            }
          >
            <link.icon className="w-[18px] h-[18px] flex-shrink-0" />
            {!collapsed && <span>{link.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="px-2 py-3">
        <button
          onClick={onToggle}
          className={`flex items-center gap-2 w-full rounded-lg py-2 text-textSecondary hover:text-textPrimary hover:bg-[rgba(255,255,255,0.06)]
                     transition-all duration-200 ${collapsed ? "justify-center px-2" : "px-3"}`}
        >
          {collapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
          {!collapsed && <span className="text-xs">Collapse</span>}
        </button>
      </div>

      {/* Footer */}
      {!collapsed && (
        <div className="px-5 py-3">
          <p className="text-xs text-textMuted">OVERWATCH v2.0</p>
        </div>
      )}
    </aside>
  );
}
