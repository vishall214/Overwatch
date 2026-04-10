import React, { useRef, useState, useCallback, useEffect } from "react";
import { useZones } from "../../hooks/useZones";
import type { Zone } from "../../api/zones";
import { useCameraStream } from "../../context/CameraStreamContext";

interface ZoneStyle {
  fillClass: string;
  borderClass: string;
  labelClass: string;
  handleClass: string;
}

const ZONE_STYLES: Record<string, ZoneStyle> = {
  intrusion: {
    fillClass: "bg-teal-400/10",
    borderClass: "border-teal-300/90",
    labelClass: "text-teal-100",
    handleClass: "bg-teal-300 border border-teal-100 shadow-sm shadow-teal-900/40",
  },
  loitering: {
    fillClass: "bg-teal-400/10",
    borderClass: "border-teal-300/90",
    labelClass: "text-teal-100",
    handleClass: "bg-teal-300 border border-teal-100 shadow-sm shadow-teal-900/40",
  },
  crowd: {
    fillClass: "bg-teal-400/10",
    borderClass: "border-teal-300/90",
    labelClass: "text-teal-100",
    handleClass: "bg-teal-300 border border-teal-100 shadow-sm shadow-teal-900/40",
  },
};

const DEFAULT_STYLE: ZoneStyle = {
  fillClass: "bg-teal-400/10",
  borderClass: "border-teal-300/90",
  labelClass: "text-teal-100",
  handleClass: "bg-teal-300 border border-teal-100 shadow-sm shadow-teal-900/40",
};

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface DragState {
  type: "move" | "nw" | "ne" | "sw" | "se";
  zoneId: number;
  startX: number;
  startY: number;
  origX: number;
  origY: number;
  origW: number;
  origH: number;
}

interface VideoViewport {
  offsetX: number;
  offsetY: number;
  width: number;
  height: number;
  containerWidth: number;
  containerHeight: number;
  videoWidth: number;
  videoHeight: number;
  canvasWidth: number;
  canvasHeight: number;
}

interface PointerSample {
  normalizedX: number;
  normalizedY: number;
  rawX: number;
  rawY: number;
  inViewport: boolean;
}

type ZoneTypeValue = "intrusion" | "loitering" | "crowd";

interface ZoneEditorProps {
  visible?: boolean;
  drawModeExternal?: boolean;
  onDrawModeChange?: (nextDrawMode: boolean) => void;
  clearSignal?: number;
  zoneTypeExternal?: ZoneTypeValue;
  showControls?: boolean;
}

const clamp01 = (value: number): number => Math.max(0, Math.min(1, value));

const computeViewport = (
  container: HTMLDivElement,
  videoWidth: number,
  videoHeight: number
): VideoViewport => {
  const rect = container.getBoundingClientRect();
  const containerWidth = Math.max(1, rect.width);
  const containerHeight = Math.max(1, rect.height);

  const sourceWidth = videoWidth > 0 ? videoWidth : containerWidth;
  const sourceHeight = videoHeight > 0 ? videoHeight : containerHeight;

  const sourceAspect = sourceWidth / sourceHeight;
  const containerAspect = containerWidth / containerHeight;

  let width = containerWidth;
  let height = containerHeight;
  let offsetX = 0;
  let offsetY = 0;

  if (containerAspect > sourceAspect) {
    height = containerHeight;
    width = height * sourceAspect;
    offsetX = (containerWidth - width) / 2;
  } else {
    width = containerWidth;
    height = width / sourceAspect;
    offsetY = (containerHeight - height) / 2;
  }

  const canvas = container.parentElement?.querySelector("canvas") as HTMLCanvasElement | null;
  const canvasRect = canvas?.getBoundingClientRect();

  return {
    offsetX,
    offsetY,
    width,
    height,
    containerWidth,
    containerHeight,
    videoWidth: sourceWidth,
    videoHeight: sourceHeight,
    canvasWidth: canvasRect?.width ?? 0,
    canvasHeight: canvasRect?.height ?? 0,
  };
};

const ZoneEditor: React.FC<ZoneEditorProps> = ({
  visible = true,
  drawModeExternal,
  onDrawModeChange,
  clearSignal,
  zoneTypeExternal,
  showControls = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { imageElement } = useCameraStream();
  const { zones, addZone, removeZone } = useZones();

  const [isDrawing, setIsDrawing] = useState(false);
  const [drawMode, setDrawMode] = useState(false);
  const [zoneType, setZoneType] = useState<ZoneTypeValue>("intrusion");
  const drawRef = useRef<Rect | null>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const clearSignalRef = useRef<number | undefined>(clearSignal);

  const dragRef = useRef<DragState | null>(null);
  const [, forceUpdate] = useState(0);

  const initialViewport: VideoViewport = {
    offsetX: 0,
    offsetY: 0,
    width: 1,
    height: 1,
    containerWidth: 1,
    containerHeight: 1,
    videoWidth: 1,
    videoHeight: 1,
    canvasWidth: 0,
    canvasHeight: 0,
  };

  const [viewport, setViewport] = useState<VideoViewport>(initialViewport);
  const viewportRef = useRef<VideoViewport>(initialViewport);

  const syncViewport = useCallback(() => {
    if (!containerRef.current) return;
    const next = computeViewport(
      containerRef.current,
      imageElement?.naturalWidth ?? 0,
      imageElement?.naturalHeight ?? 0
    );
    viewportRef.current = next;
    setViewport(next);
  }, [imageElement]);

  useEffect(() => {
    if (!containerRef.current) return;

    syncViewport();

    const observer = new ResizeObserver(() => {
      syncViewport();
    });

    observer.observe(containerRef.current);
    window.addEventListener("resize", syncViewport);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", syncViewport);
    };
  }, [syncViewport]);

  useEffect(() => {
    if (typeof drawModeExternal !== "boolean") return;
    setDrawMode(drawModeExternal);
  }, [drawModeExternal]);

  useEffect(() => {
    if (!zoneTypeExternal) return;
    setZoneType(zoneTypeExternal);
  }, [zoneTypeExternal]);

  useEffect(() => {
    onDrawModeChange?.(drawMode);
  }, [drawMode, onDrawModeChange]);

  const pointerToNormalized = useCallback((e: React.MouseEvent): PointerSample | null => {
    const container = containerRef.current;
    if (!container) return null;

    const vp = viewportRef.current;
    if (vp.width <= 0 || vp.height <= 0) return null;

    const rect = container.getBoundingClientRect();
    const rawX = e.clientX - rect.left;
    const rawY = e.clientY - rect.top;
    const localX = rawX - vp.offsetX;
    const localY = rawY - vp.offsetY;
    const inViewport = localX >= 0 && localX <= vp.width && localY >= 0 && localY <= vp.height;

    return {
      normalizedX: clamp01(localX / vp.width),
      normalizedY: clamp01(localY / vp.height),
      rawX,
      rawY,
      inViewport,
    };
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!drawMode || !containerRef.current) return;
      const point = pointerToNormalized(e);
      if (!point || !point.inViewport) return;

      const x = point.normalizedX;
      const y = point.normalizedY;

      drawRef.current = { x, y, w: 0, h: 0 };
      setIsDrawing(true);
    },
    [drawMode, pointerToNormalized]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const point = pointerToNormalized(e);
      if (!point) return;

      if (isDrawing && drawRef.current) {
        const cx = point.normalizedX;
        const cy = point.normalizedY;
        drawRef.current.w = cx - drawRef.current.x;
        drawRef.current.h = cy - drawRef.current.y;

        if (previewRef.current) {
          const d = drawRef.current;
          const left = Math.min(d.x, d.x + d.w) * 100;
          const top = Math.min(d.y, d.y + d.h) * 100;
          const width = Math.abs(d.w) * 100;
          const height = Math.abs(d.h) * 100;
          const style = previewRef.current.style;
          style.left = `${left}%`;
          style.top = `${top}%`;
          style.width = `${width}%`;
          style.height = `${height}%`;
          style.display = "block";
        }
        return;
      }

      if (dragRef.current) {
        const ds = dragRef.current;
        const dx = point.normalizedX - ds.startX;
        const dy = point.normalizedY - ds.startY;

        const zone = zones.find((z) => z.id === ds.zoneId);
        if (!zone) return;

        let nx = zone.x;
        let ny = zone.y;
        let nw = zone.width;
        let nh = zone.height;

        if (ds.type === "move") {
          nx = Math.max(0, Math.min(1 - ds.origW, ds.origX + dx));
          ny = Math.max(0, Math.min(1 - ds.origH, ds.origY + dy));
          nw = ds.origW;
          nh = ds.origH;
        } else {
          let x1 = ds.origX;
          let y1 = ds.origY;
          let x2 = ds.origX + ds.origW;
          let y2 = ds.origY + ds.origH;

          if (ds.type.includes("w")) x1 = Math.max(0, ds.origX + dx);
          if (ds.type.includes("e")) x2 = Math.min(1, ds.origX + ds.origW + dx);
          if (ds.type.includes("n")) y1 = Math.max(0, ds.origY + dy);
          if (ds.type.includes("s")) y2 = Math.min(1, ds.origY + ds.origH + dy);

          nx = Math.min(x1, x2);
          ny = Math.min(y1, y2);
          nw = Math.abs(x2 - x1);
          nh = Math.abs(y2 - y1);
        }

        (zone as Zone & { x: number; y: number; width: number; height: number }).x = nx;
        (zone as Zone & { x: number; y: number; width: number; height: number }).y = ny;
        (zone as Zone & { x: number; y: number; width: number; height: number }).width = nw;
        (zone as Zone & { x: number; y: number; width: number; height: number }).height = nh;
        forceUpdate((n) => n + 1);
      }
    },
    [isDrawing, pointerToNormalized, zones]
  );

  const handleMouseUp = useCallback(() => {
    if (isDrawing && drawRef.current) {
      const d = drawRef.current;
      const x = Math.min(d.x, d.x + d.w);
      const y = Math.min(d.y, d.y + d.h);
      const w = Math.abs(d.w);
      const h = Math.abs(d.h);

      if (w > 0.01 && h > 0.01) {
        const payload = { type: zoneType, x, y, width: w, height: h };
        addZone(payload);
      }
      drawRef.current = null;
      if (previewRef.current) previewRef.current.style.display = "none";
      setIsDrawing(false);
      setDrawMode(false);
      return;
    }

    if (dragRef.current) {
      const zone = zones.find((z) => z.id === dragRef.current!.zoneId);
      if (zone) {
        const { type, x, y, width, height, name } = zone;
        removeZone(zone.id);
        addZone({ type, x, y, width, height, name: name ?? undefined });
      }
      dragRef.current = null;
    }
  }, [isDrawing, zoneType, addZone, removeZone, zones]);

  useEffect(() => {
    const up = () => handleMouseUp();
    window.addEventListener("mouseup", up);
    return () => window.removeEventListener("mouseup", up);
  }, [handleMouseUp]);

  const startDrag = useCallback(
    (e: React.MouseEvent, zone: Zone, type: DragState["type"]) => {
      e.stopPropagation();
      e.preventDefault();
      const point = pointerToNormalized(e);
      if (!point) return;

      dragRef.current = {
        type,
        zoneId: zone.id,
        startX: point.normalizedX,
        startY: point.normalizedY,
        origX: zone.x,
        origY: zone.y,
        origW: zone.width,
        origH: zone.height,
      };
    },
    [pointerToNormalized]
  );

  const handleClearAll = useCallback(() => {
    zones.forEach((z) => removeZone(z.id));
  }, [zones, removeZone]);

  useEffect(() => {
    if (typeof clearSignal !== "number") return;

    if (clearSignalRef.current === undefined) {
      clearSignalRef.current = clearSignal;
      return;
    }

    if (clearSignal !== clearSignalRef.current) {
      clearSignalRef.current = clearSignal;
      handleClearAll();
    }
  }, [clearSignal, handleClearAll]);

  const getZoneStyle = (type: string): ZoneStyle => ZONE_STYLES[type] ?? DEFAULT_STYLE;
  const previewStyle = getZoneStyle(zoneType);
  const cursorClass = drawMode ? "cursor-crosshair" : "cursor-default";

  if (!visible) return null;

  return (
    <div
      ref={containerRef}
      className={`absolute inset-0 z-10 ${cursorClass}`}
      style={{ pointerEvents: "auto" }}
    >
      <div
        className="absolute"
        style={{
          pointerEvents: "auto",
          left: viewport.offsetX,
          top: viewport.offsetY,
          width: viewport.width,
          height: viewport.height,
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      >
        {zones.map((zone) => {
          const style = getZoneStyle(zone.type);

          return (
            <div
              key={zone.id}
              className={`absolute group border-2 transition-shadow duration-200 hover:shadow-[0_0_12px_rgba(45,212,191,0.25)] ${style.fillClass} ${style.borderClass}`}
              style={{
                left: `${zone.x * 100}%`,
                top: `${zone.y * 100}%`,
                width: `${zone.width * 100}%`,
                height: `${zone.height * 100}%`,
                pointerEvents: "auto",
              }}
              onMouseDown={(e) => !drawMode && startDrag(e, zone, "move")}
            >
              <span
                className={`absolute top-0.5 left-1 text-[10px] font-mono uppercase tracking-wider select-none ${style.labelClass}`}
              >
                {zone.name ?? zone.type}
              </span>

              <button
                className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-threat-critical text-bg text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer pointer-events-auto z-20"
                onClick={(e) => {
                  e.stopPropagation();
                  removeZone(zone.id);
                }}
              >
                x
              </button>

              {(["nw", "ne", "sw", "se"] as const).map((corner) => {
                const pos: React.CSSProperties = {};
                if (corner.includes("n")) pos.top = -4;
                if (corner.includes("s")) pos.bottom = -4;
                if (corner.includes("w")) pos.left = -4;
                if (corner.includes("e")) pos.right = -4;
                const cursorMap = {
                  nw: "nwse-resize",
                  ne: "nesw-resize",
                  sw: "nesw-resize",
                  se: "nwse-resize",
                };

                return (
                  <div
                    key={corner}
                    className={`absolute w-2.5 h-2.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity pointer-events-auto z-20 ${style.handleClass}`}
                    style={{
                      ...pos,
                      cursor: cursorMap[corner],
                    }}
                    onMouseDown={(e) => !drawMode && startDrag(e, zone, corner)}
                  />
                );
              })}
            </div>
          );
        })}

        <div
          ref={previewRef}
          className={`absolute border-2 border-dashed pointer-events-none hidden ${previewStyle.fillClass} ${previewStyle.borderClass}`}
        />
      </div>

      {showControls ? (
        <div
          className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 rounded-xl bg-bg/80 backdrop-blur-lg border border-border shadow-lg z-30"
          style={{ pointerEvents: "auto" }}
        >
          <button
            onClick={() => setDrawMode((d) => !d)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
              drawMode
                ? "bg-accent text-bg"
                : "bg-surface text-textSecondary hover:bg-card"
            }`}
          >
            {drawMode ? "Drawing..." : "Draw Zone"}
          </button>

          <select
            value={zoneType}
            onChange={(e) => setZoneType(e.target.value as ZoneTypeValue)}
            className="px-2 py-1.5 rounded-lg text-xs bg-surface text-textPrimary border border-border outline-none cursor-pointer appearance-none"
          >
            <option value="intrusion">Intrusion</option>
            <option value="loitering">Loitering</option>
            <option value="crowd">Crowd</option>
          </select>

          {zones.length > 0 && (
            <button
              onClick={handleClearAll}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider bg-threat-critical/20 text-threat-critical hover:bg-threat-critical/30 transition-colors"
            >
              Clear All
            </button>
          )}
        </div>
      ) : null}
    </div>
  );
};

export default React.memo(ZoneEditor);
