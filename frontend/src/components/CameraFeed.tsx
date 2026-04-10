import React, { useRef, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { getSourceInfo } from "../api/video";
import { useCameraStream } from "../context/CameraStreamContext";

type CameraModule = "intrusion" | "loitering" | "crowd" | "weapon_detection";

interface CameraFeedProps {
  moduleType?: CameraModule;
}

const MODULE_LABELS: Record<CameraModule, string> = {
  intrusion: "Intrusion",
  loitering: "Loitering",
  crowd: "Crowd",
  weapon_detection: "Weapons",
};

function OverlayCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-bg/50 backdrop-blur-sm">
      <div className="glass px-6 py-4 rounded-xl text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-textPrimary">{title}</p>
        <p className="mt-2 text-xs text-textSecondary">{description}</p>
      </div>
    </div>
  );
}

function OfflineOverlay() {
  return <OverlayCard title="Camera Offline" description="Start the camera pipeline from the top bar." />;
}

/**
 * CameraFeed — canvas-smoothed MJPEG renderer.
 * Loads the MJPEG stream into a hidden <img>, then paints each
 * decoded frame onto a <canvas> via requestAnimationFrame for
 * smooth, tear-free display even at low backend FPS.
 */
const CameraFeed = React.memo(function CameraFeed({ moduleType }: CameraFeedProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const { imageElement, cameraOnline } = useCameraStream();
  const isCameraRunning = cameraOnline;
  const { data: sourceInfo, isLoading: sourceLoading } = useQuery({
    queryKey: ["sourceInfo"],
    queryFn: getSourceInfo,
    enabled: Boolean(moduleType) && isCameraRunning,
    refetchInterval: 2000,
  });

  const activeModule = sourceInfo?.active_module;
  const moduleMatches = Boolean(moduleType && activeModule && activeModule === moduleType);

  const paint = useCallback(() => {
    const canvas = canvasRef.current;
    if (canvas && imageElement && imageElement.naturalWidth > 0 && moduleMatches) {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        if (canvas.width !== imageElement.naturalWidth || canvas.height !== imageElement.naturalHeight) {
          canvas.width = imageElement.naturalWidth;
          canvas.height = imageElement.naturalHeight;
        }
        ctx.drawImage(imageElement, 0, 0);
      }
    }
    rafRef.current = requestAnimationFrame(paint);
  }, [imageElement, moduleMatches]);

  useEffect(() => {
    const canvas = canvasRef.current;

    if (!isCameraRunning || !imageElement || !moduleMatches) {
      cancelAnimationFrame(rafRef.current);

      if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      }

      return;
    }

    rafRef.current = requestAnimationFrame(paint);

    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, [isCameraRunning, imageElement, moduleMatches, paint]);

  if (!isCameraRunning) {
    cancelAnimationFrame(rafRef.current);

    return (
      <div className="relative w-full h-full rounded-2xl glass-strong p-2 pointer-events-none">
        <div className="relative w-full h-full rounded-xl overflow-hidden">
          <OfflineOverlay />
          <div className="absolute bottom-4 left-4 px-3 py-1 rounded-lg glass">
            <span className="text-xs text-textMuted font-mono">OVERWATCH - Primary Feed</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full rounded-2xl glass-strong p-2 pointer-events-none">
      <div className="relative w-full h-full rounded-xl overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full h-full object-contain bg-bg pointer-events-none"
        />

        {!moduleType ? (
          <OverlayCard title="Module Required" description="Select a module before rendering the camera stream." />
        ) : sourceLoading || !activeModule ? (
          <OverlayCard title="Syncing Module" description="Waiting for the active source module to be confirmed." />
        ) : moduleMatches ? (
          <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 rounded-full bg-threat-critical/10 backdrop-blur-md border border-threat-critical/40">
            <span className="w-2 h-2 rounded-full bg-threat-critical animate-pulse" />
            <span className="text-xs font-semibold text-threat-critical uppercase tracking-wider">Live</span>
          </div>
        ) : (
          <OverlayCard
            title="Module Inactive"
            description={`Source is currently active in ${MODULE_LABELS[activeModule as CameraModule] ?? "another"}.`}
          />
        )}

        {/* Overlay label */}
        <div className="absolute bottom-4 left-4 px-3 py-1 rounded-lg glass">
          <span className="text-xs text-textMuted font-mono">OVERWATCH - Primary Feed</span>
        </div>
      </div>
    </div>
  );
});

export default CameraFeed;
