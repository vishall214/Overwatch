import { useEffect } from "react";
import CameraFeed from "../components/CameraFeed";
import AlertsPanel from "../components/AlertsPanel";
import SourceSelector from "../components/SourceSelector";
import { useToggleModule } from "../hooks/useModules";
import { Eye } from "lucide-react";

export default function Loitering() {
  const toggleMutation = useToggleModule();

  useEffect(() => {
    toggleMutation.mutate({ name: "loitering", enable: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="rounded-2xl glass-panel p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ow-alert-loitering to-orange-600 flex items-center justify-center">
            <Eye className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-ow-light/90">Loitering Detection</h2>
            <p className="text-sm text-ow-mist/45">Behavioral analysis for lingering individuals</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-ow-mist/55">
          <div className="p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]">
            <span className="text-ow-mist/30 text-xs uppercase tracking-wider">How it works</span>
            <p className="mt-1">Analyzes tracked individuals' dwell time in monitored zones to detect loitering behavior.</p>
          </div>
          <div className="p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]">
            <span className="text-ow-mist/30 text-xs uppercase tracking-wider">Model</span>
            <p className="mt-1">DeepSORT tracking combined with temporal analysis and zone residency thresholds.</p>
          </div>
          <div className="p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]">
            <span className="text-ow-mist/30 text-xs uppercase tracking-wider">Response</span>
            <p className="mt-1">Alerts generated when dwell time exceeds configurable threshold per zone.</p>
          </div>
        </div>
      </div>

      {/* Camera + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <SourceSelector moduleType="loitering" />
          <div className="h-[50vh] min-h-[350px]">
            <CameraFeed />
          </div>
        </div>
        <AlertsPanel />
      </div>
    </div>
  );
}
