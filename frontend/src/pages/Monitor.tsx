import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import CameraFeed from "../components/CameraFeed";
import SourceSelector from "../components/SourceSelector";
import SystemStatus from "../components/SystemStatus";
import AlertsPanel from "../components/AlertsPanel";

type MonitorModule = "intrusion" | "loitering" | "crowd" | "weapon_detection";

type ModuleTab = {
  label: string;
  module: MonitorModule;
  queryValue: string;
};

const MODULE_TABS: ModuleTab[] = [
  { label: "Intrusion", module: "intrusion", queryValue: "intrusion" },
  { label: "Loitering", module: "loitering", queryValue: "loitering" },
  { label: "Crowd", module: "crowd", queryValue: "crowd" },
  { label: "Weapons", module: "weapon_detection", queryValue: "weapons" },
];

function parseModuleQuery(value: string | null): MonitorModule | null {
  if (!value) return null;
  if (value === "weapons" || value === "weapon_detection") return "weapon_detection";
  if (value === "intrusion" || value === "loitering" || value === "crowd") return value;
  return null;
}

function toModuleQuery(module: MonitorModule): string {
  if (module === "weapon_detection") return "weapons";
  return module;
}

export default function Monitor() {
  const [searchParams, setSearchParams] = useSearchParams();
  const moduleFromQuery = useMemo(() => parseModuleQuery(searchParams.get("module")), [searchParams]);
  const [activeModule, setActiveModule] = useState<MonitorModule>(moduleFromQuery ?? "intrusion");

  useEffect(() => {
    if (moduleFromQuery && moduleFromQuery !== activeModule) {
      setActiveModule(moduleFromQuery);
    }
  }, [moduleFromQuery, activeModule]);

  useEffect(() => {
    if (moduleFromQuery) return;
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("module", toModuleQuery(activeModule));
    setSearchParams(nextParams, { replace: true });
  }, [activeModule, moduleFromQuery, searchParams, setSearchParams]);

  function handleModuleChange(module: MonitorModule) {
    setActiveModule(module);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("module", toModuleQuery(module));
    setSearchParams(nextParams, { replace: true });
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-4">
        <div className="glass rounded-xl p-3">
          <p className="text-xs font-semibold text-textSecondary uppercase tracking-wider mb-2">Active Module</p>
          <div className="flex flex-wrap gap-2">
            {MODULE_TABS.map((tab) => {
              const isActive = tab.module === activeModule;
              return (
                <button
                  key={tab.module}
                  type="button"
                  onClick={() => handleModuleChange(tab.module)}
                  className={[
                    "px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive ? "bg-card text-textPrimary" : "bg-surface text-textSecondary hover:text-textPrimary",
                  ].join(" ")}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
        <SourceSelector moduleType={activeModule} />
      </div>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 xl:col-span-8">
          <div className="aspect-video max-h-[520px] w-full">
            <CameraFeed moduleType={activeModule} />
          </div>
        </div>

        <div className="col-span-12 xl:col-span-4 flex flex-col gap-4">
          <SystemStatus activeModule={activeModule} />
          <AlertsPanel compact />
        </div>
      </div>
    </div>
  );
}
