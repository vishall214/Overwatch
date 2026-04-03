import { useEffect } from "react";
import CameraFeed from "../components/CameraFeed";
import AlertsPanel from "../components/AlertsPanel";
import { useToggleModule } from "../hooks/useModules";
import { Crosshair } from "lucide-react";

export default function Weapons() {
  const toggleMutation = useToggleModule();

  useEffect(() => {
    toggleMutation.mutate({ name: "weapon_detection", enable: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="rounded-2xl glass-panel p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 to-red-700 flex items-center justify-center">
            <Crosshair className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-ow-light/90">Weapon Detection</h2>
            <p className="text-sm text-ow-mist/45">Dangerous object identification with temporal filtering</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-ow-mist/55">
          <div className="p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]">
            <span className="text-ow-mist/30 text-xs uppercase tracking-wider">How it works</span>
            <p className="mt-1">A dedicated YOLO model runs parallel inference to identify knives, guns, and other dangerous objects in the scene.</p>
          </div>
          <div className="p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]">
            <span className="text-ow-mist/30 text-xs uppercase tracking-wider">Model</span>
            <p className="mt-1">Separate weapon-trained YOLO model with temporal filtering — 5 consecutive detections required before alert.</p>
          </div>
          <div className="p-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)]">
            <span className="text-ow-mist/30 text-xs uppercase tracking-wider">Response</span>
            <p className="mt-1">Alerts include snapshot, object class, confidence score, and 10-second cooldown to prevent flooding.</p>
          </div>
        </div>
      </div>

      {/* Camera + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 h-[50vh] min-h-[350px]">
          <CameraFeed />
        </div>
        <AlertsPanel />
      </div>
    </div>
  );
}
