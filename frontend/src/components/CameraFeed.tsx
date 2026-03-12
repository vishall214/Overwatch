import React, { useRef, useEffect, useCallback } from "react";
import { API } from "../api/config";

/**
 * CameraFeed — canvas-smoothed MJPEG renderer.
 * Loads the MJPEG stream into a hidden <img>, then paints each
 * decoded frame onto a <canvas> via requestAnimationFrame for
 * smooth, tear-free display even at low backend FPS.
 */
const CameraFeed = React.memo(function CameraFeed() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const rafRef = useRef<number>(0);

  const paint = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (canvas && img && img.naturalWidth > 0) {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        if (canvas.width !== img.naturalWidth || canvas.height !== img.naturalHeight) {
          canvas.width = img.naturalWidth;
          canvas.height = img.naturalHeight;
        }
        ctx.drawImage(img, 0, 0);
      }
    }
    rafRef.current = requestAnimationFrame(paint);
  }, []);

  useEffect(() => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = API.camera.stream;
    imgRef.current = img;
    rafRef.current = requestAnimationFrame(paint);
    return () => {
      cancelAnimationFrame(rafRef.current);
      img.src = "";
      imgRef.current = null;
    };
  }, [paint]);

  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden glass-panel-heavy scanline">
      <canvas
        ref={canvasRef}
        className="w-full h-full object-contain bg-ow-bg"
      />
      {/* Live indicator */}
      <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 rounded-full bg-ow-alert-intrusion/15 backdrop-blur-md border border-ow-alert-intrusion/25">
        <span className="w-2 h-2 rounded-full bg-ow-alert-intrusion animate-pulse" />
        <span className="text-xs font-semibold text-ow-alert-intrusion/80 uppercase tracking-wider">Live</span>
      </div>
      {/* Overlay label */}
      <div className="absolute bottom-4 left-4 px-3 py-1 rounded-lg bg-ow-bg/60 backdrop-blur-sm">
        <span className="text-xs text-ow-mist/60 font-mono">OVERWATCH — Primary Feed</span>
      </div>
    </div>
  );
});

export default CameraFeed;
