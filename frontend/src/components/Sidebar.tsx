import { NavLink } from "react-router-dom";
import { BarChart3, Bell, Eye, FileText, LayoutDashboard, PanelLeft, PanelLeftClose } from "lucide-react";

const links = [
  { to: "/monitor", label: "Monitor", icon: LayoutDashboard },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/reports", label: "Reports", icon: FileText },
];

export default function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <aside
      className={`fixed left-0 top-0 z-40 flex h-screen flex-col px-2 pb-3 pt-3 page-transition ${
        collapsed ? "w-[72px]" : "w-[226px]"
      }`}
    >
      <div className="glass-card flex h-full flex-col overflow-hidden">
        <div className={`flex items-center ${collapsed ? "justify-center px-2 py-4" : "justify-start px-4 py-4"}`}>
          <NavLink to="/" className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10 text-accent">
              <Eye className="h-4.5 w-4.5" />
            </span>
            {!collapsed ? <span className="text-sm font-semibold tracking-[0.2em] text-textPrimary">OVERWATCH</span> : null}
          </NavLink>
        </div>

        <nav className="flex-1 space-y-1 px-2 py-2">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              title={collapsed ? link.label : undefined}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium page-transition ${
                  collapsed ? "justify-center" : "justify-start"
                } ${
                  isActive
                    ? "bg-teal-500/20 border border-teal-400/40 text-textPrimary"
                    : "border border-transparent text-textSecondary hover:text-textPrimary hover:bg-white/5"
                }`
              }
            >
              <link.icon className="h-[18px] w-[18px] flex-shrink-0" />
              {!collapsed ? <span>{link.label}</span> : null}
            </NavLink>
          ))}
        </nav>

        <div className="px-2 pb-2">
          <button
            type="button"
            onClick={onToggle}
            className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-textSecondary page-transition hover:bg-white/5 hover:text-textPrimary ${
              collapsed ? "justify-center" : "justify-start"
            }`}
          >
            {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            {!collapsed ? <span>Collapse</span> : null}
          </button>
        </div>
      </div>
    </aside>
  );
}
