import { useRef, useEffect } from "react";
import gsap from "gsap";
import { useModules, useToggleModule } from "../hooks/useModules";
import { ShieldAlert, Eye, Users, Crosshair } from "lucide-react";

const moduleConfig = [
  { name: "intrusion", label: "Intrusion Detection", icon: ShieldAlert, color: "text-threat-critical" },
  { name: "loitering", label: "Loitering Detection", icon: Eye, color: "text-threat-high" },
  { name: "crowd", label: "Crowd Detection", icon: Users, color: "text-threat-info" },
  { name: "weapon_detection", label: "Weapon Detection", icon: Crosshair, color: "text-threat-critical" },
] as const;

export default function ModuleControls() {
  const { data: modules, isLoading } = useModules();
  const toggleMutation = useToggleModule();

  return (
    <div className="glass glass-hover rounded-xl p-4 h-full hover:shadow-[0_0_10px_rgba(36,158,148,0.2)]">
      <h3 className="text-sm font-semibold text-textSecondary uppercase tracking-wider mb-3">Modules</h3>
      <div className="space-y-2">
        {isLoading ? (
          <div className="text-textSecondary text-sm text-center py-4">Loading...</div>
        ) : (
          moduleConfig.map((mod) => {
            const enabled = modules?.[mod.name] ?? false;
            return (
              <ModuleToggle
                key={mod.name}
                label={mod.label}
                icon={<mod.icon className={`w-4 h-4 ${mod.color}`} />}
                enabled={enabled}
                loading={toggleMutation.isPending}
                onToggle={() =>
                  toggleMutation.mutate({ name: mod.name, enable: !enabled })
                }
              />
            );
          })
        )}
      </div>
    </div>
  );
}

function ModuleToggle({
  label,
  icon,
  enabled,
  loading,
  onToggle,
}: {
  label: string;
  icon: React.ReactNode;
  enabled: boolean;
  loading: boolean;
  onToggle: () => void;
}) {
  const knobRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!knobRef.current) return;
    const tween = gsap.to(knobRef.current, {
      x: enabled ? 20 : 0,
      duration: 0.3,
      ease: "power2.out",
      overwrite: "auto",
    });

    return () => {
      tween.kill();
    };
  }, [enabled]);

  return (
    <button
      onClick={onToggle}
      disabled={loading}
      className="w-full flex items-center justify-between p-3 rounded-xl bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] hover:bg-[rgba(255,255,255,0.06)] transition-colors duration-200 group disabled:opacity-50"
    >
      <div className="flex items-center gap-3">
        {icon}
        <span className="text-sm text-textPrimary transition-colors">{label}</span>
      </div>
      <div
        className={`relative w-11 h-6 rounded-full transition-colors duration-300 ${
          enabled ? "bg-[rgba(36,158,148,0.2)] border-[rgba(36,158,148,0.45)]" : "bg-[rgba(255,255,255,0.05)] border-[rgba(255,255,255,0.12)]"
        } border`}
      >
        <div
          ref={knobRef}
          className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-colors duration-300 ${
            enabled ? "bg-accent" : "bg-textMuted"
          }`}
        />
      </div>
    </button>
  );
}
