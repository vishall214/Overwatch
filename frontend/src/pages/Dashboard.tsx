import CameraFeed from "../components/CameraFeed";
import AlertsPanel from "../components/AlertsPanel";
import SystemStatus from "../components/SystemStatus";
import ModuleControls from "../components/ModuleControls";

export default function Dashboard() {
  return (
    <div className="grid grid-cols-12 gap-4">
      {/* Camera Feed — spans 8 columns */}
      <div className="col-span-12 xl:col-span-8 h-[55vh] min-h-[400px]">
        <CameraFeed />
      </div>

      {/* Right column: System + Modules stacked */}
      <div className="col-span-12 xl:col-span-4 flex flex-col gap-4">
        <SystemStatus />
        <ModuleControls />
      </div>

      {/* Full-width alerts below */}
      <div className="col-span-12">
        <AlertsPanel />
      </div>
    </div>
  );
}
