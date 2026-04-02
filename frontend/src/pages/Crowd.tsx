import { useEffect } from "react";
import CameraFeed from "../components/CameraFeed";
import AlertsPanel from "../components/AlertsPanel";
import SourceSelector from "../components/SourceSelector";
import { useToggleModule } from "../hooks/useModules";
import { Users } from "lucide-react";

export default function Crowd() {
  const toggleMutation = useToggleModule();

  useEffect(() => {
    toggleMutation.mutate({ name: "crowd", enable: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="rounded-2xl glass-panel p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ow-alert-crowd to-blue-600 flex items-center justify-center">
            <Users className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-ow-light/90">Crowd Detection</h2>
            <p className="text-sm text-ow-mist/45">Real-time crowd density estimation</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-ow-mist/55">
          <div className="p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]">
            <span className="text-ow-mist/30 text-xs uppercase tracking-wider">How it works</span>
            <p className="mt-1">Counts detected persons per zone and triggers alerts when density exceeds thresholds.</p>
          </div>
          <div className="p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]">
            <span className="text-ow-mist/30 text-xs uppercase tracking-wider">Model</span>
            <p className="mt-1">YOLOv8 person detection with spatial clustering and configurable crowd limits.</p>
          </div>
          <div className="p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]">
            <span className="text-ow-mist/30 text-xs uppercase tracking-wider">Response</span>
            <p className="mt-1">Crowd count alerts with zone-specific density snapshots for review.</p>
          </div>
        </div>
      </div>

      {/* Camera + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <SourceSelector moduleType="crowd" />
          <div className="h-[50vh] min-h-[350px]">
            <CameraFeed />
          </div>
        </div>
        <AlertsPanel />
      </div>
    </div>
  );
}
