import { useRef, useEffect } from "react";
import gsap from "gsap";
import { useModules, useToggleModule } from "../hooks/useModules";
import { ShieldAlert, Eye, Users } from "lucide-react";

const moduleConfig = [
  { name: "intrusion", label: "Intrusion Detection", icon: ShieldAlert, color: "text-ow-alert-intrusion" },
  { name: "loitering", label: "Loitering Detection", icon: Eye, color: "text-ow-alert-loitering" },
  { name: "crowd", label: "Crowd Detection", icon: Users, color: "text-ow-alert-crowd" },
] as const;

export default function ModuleControls() {
  const { data: modules, isLoading } = useModules();
  const toggleMutation = useToggleModule();

  return (
    <div className="glass-panel rounded-2xl p-4 h-full">
      <h3 className="text-sm font-semibold text-ow-mist/70 uppercase tracking-wider mb-3">Modules</h3>
      <div className="space-y-2">
        {isLoading ? (
          <div className="text-ow-mist/30 text-sm text-center py-4">Loading...</div>
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
    gsap.to(knobRef.current, {
      x: enabled ? 20 : 0,
      duration: 0.3,
      ease: "power2.out",
    });
  }, [enabled]);

  return (
    <button
      onClick={onToggle}
      disabled={loading}
      className="w-full flex items-center justify-between p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]
                 hover:bg-ow-teal/15 hover:border-ow-accent/10 transition-all duration-200 group disabled:opacity-50"
    >
      <div className="flex items-center gap-3">
        {icon}
        <span className="text-sm text-ow-light/80 group-hover:text-ow-light transition-colors">{label}</span>
      </div>
      <div
        className={`relative w-11 h-6 rounded-full transition-colors duration-300 ${
          enabled ? "bg-ow-accent/25 border-ow-accent/35" : "bg-ow-teal/20 border-ow-teal/15"
        } border`}
      >
        <div
          ref={knobRef}
          className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full transition-colors duration-300 ${
            enabled ? "bg-ow-accent shadow-lg shadow-ow-accent/30" : "bg-ow-mist/40"
          }`}
        />
      </div>
    </button>
  );
}
