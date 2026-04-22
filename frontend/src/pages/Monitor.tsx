import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import CameraFeed from "../components/CameraFeed";
import SourceSelector from "../components/SourceSelector";
import SystemStatus from "../components/SystemStatus";
import AlertsPanel from "../components/AlertsPanel";
import ZoneEditor from "../components/zones/ZoneEditor";

type MonitorModule = "intrusion" | "loitering" | "crowd" | "weapon_detection";
type ZoneType = "intrusion" | "loitering" | "crowd";

type ModuleTab = {
  label: string;
  module: MonitorModule;
  queryValue: string;
};

const MODULE_TABS: ModuleTab[] = [
  { label: "Intrusion", module: "intrusion", queryValue: "intrusion" },
  { label: "Loitering", module: "loitering", queryValue: "loitering" },
  { label: "Crowd", module: "crowd", queryValue: "crowd" },
  { label: "Weapons", module: "weapon_detection", queryValue: "weapon_detection" },
];

function parseModuleQuery(value: string | null): MonitorModule | null {
  if (!value) return null;
  if (value === "weapons" || value === "weapon_detection") return "weapon_detection";
  if (value === "intrusion" || value === "loitering" || value === "crowd") return value;
  return null;
}

function toModuleQuery(module: MonitorModule): string {
  return module;
}

function toZoneType(module: MonitorModule): ZoneType {
  if (module === "weapon_detection") return "intrusion";
  return module;
}

export default function Monitor() {
  const [searchParams, setSearchParams] = useSearchParams();
  const moduleFromQuery = useMemo(() => parseModuleQuery(searchParams.get("module")), [searchParams]);
  const [activeModule, setActiveModule] = useState<MonitorModule>(moduleFromQuery ?? "intrusion");
  const [showZones, setShowZones] = useState(true);
  const [drawZones, setDrawZones] = useState(false);
  const [clearZonesSignal, setClearZonesSignal] = useState(0);
  const activeZoneType = useMemo(() => toZoneType(activeModule), [activeModule]);

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
    setDrawZones(false);
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
          <div className="space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <button
                type="button"
                onClick={() => {
                  if (!showZones) setShowZones(true);
                  setDrawZones((previous) => !previous);
                }}
                className={`glass-card px-3 py-1 rounded-lg text-sm hover:scale-[1.02] transition-all border ${
                  drawZones
                    ? "border-teal-400 bg-teal-500/20 text-white"
                    : "border-border text-textSecondary hover:text-textPrimary"
                }`}
              >
                Draw
              </button>

              <button
                type="button"
                onClick={() => setClearZonesSignal((previous) => previous + 1)}
                className="glass-card px-3 py-1 rounded-lg text-sm hover:scale-[1.02] transition-all border border-border text-textSecondary hover:text-textPrimary"
              >
                Clear
              </button>

              <button
                type="button"
                onClick={() => {
                  setShowZones((previous) => {
                    const next = !previous;
                    if (!next) setDrawZones(false);
                    return next;
                  });
                }}
                className={`glass-card px-3 py-1 rounded-lg text-sm hover:scale-[1.02] transition-all border ${
                  showZones
                    ? "border-teal-400/70 bg-teal-500/10 text-white"
                    : "border-border text-textSecondary hover:text-textPrimary"
                }`}
              >
                Toggle Zones
              </button>
            </div>

            <div className="relative aspect-video max-h-[520px] w-full">
              <CameraFeed moduleType={activeModule} />

              <div className="absolute inset-0 z-10">
                <ZoneEditor
                  visible={showZones}
                  drawModeExternal={drawZones}
                  onDrawModeChange={setDrawZones}
                  clearSignal={clearZonesSignal}
                  zoneTypeExternal={activeZoneType}
                  showControls={false}
                />
              </div>
            </div>
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
