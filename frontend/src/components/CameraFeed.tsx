import React, { useRef, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { getSourceInfo } from "../api/video";
import { useCameraStream } from "../context/CameraStreamContext";

interface CameraFeedProps {
  moduleType?: "intrusion" | "loitering" | "crowd";
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
  const { data: sourceInfo } = useQuery({
    queryKey: ["sourceInfo"],
    queryFn: getSourceInfo,
    enabled: Boolean(moduleType) && cameraOnline,
    refetchInterval: 2000,
  });

  const moduleMatches =
    !moduleType ||
    !sourceInfo?.active_module ||
    sourceInfo.active_module === moduleType;

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

    if (!cameraOnline || !imageElement || !moduleMatches) {
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
  }, [cameraOnline, imageElement, moduleMatches, paint]);

  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden glass-panel-heavy scanline">
      <canvas
        ref={canvasRef}
        className="w-full h-full object-contain bg-ow-bg"
      />

      {cameraOnline && moduleMatches ? (
        <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 rounded-full bg-ow-alert-intrusion/15 backdrop-blur-md border border-ow-alert-intrusion/25">
          <span className="w-2 h-2 rounded-full bg-ow-alert-intrusion animate-pulse" />
          <span className="text-xs font-semibold text-ow-alert-intrusion/80 uppercase tracking-wider">Live</span>
        </div>
      ) : cameraOnline ? (
        <div className="absolute inset-0 flex items-center justify-center bg-ow-bg/45 backdrop-blur-sm">
          <div className="rounded-2xl border border-[rgba(255,255,255,0.08)] bg-ow-teal/10 px-5 py-4 text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-ow-mist/80">Module Inactive</p>
            <p className="mt-2 text-xs text-ow-mist/55">
              Source is currently active in {sourceInfo?.active_module ?? "another"} module.
            </p>
          </div>
        </div>
      ) : (
        <div className="absolute inset-0 flex items-center justify-center bg-ow-bg/45 backdrop-blur-sm">
          <div className="rounded-2xl border border-[rgba(255,255,255,0.08)] bg-ow-teal/10 px-5 py-4 text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-ow-mist/80">Camera Offline</p>
            <p className="mt-2 text-xs text-ow-mist/55">Start the camera pipeline from the dashboard top bar.</p>
          </div>
        </div>
      )}

      {/* Overlay label */}
      <div className="absolute bottom-4 left-4 px-3 py-1 rounded-lg bg-ow-bg/60 backdrop-blur-sm">
        <span className="text-xs text-ow-mist/60 font-mono">OVERWATCH — Primary Feed</span>
      </div>
    </div>
  );
});

export default CameraFeed;
