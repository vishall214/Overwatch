import React, { useRef, useState, useCallback, useEffect } from "react";
import { useZones } from "../../hooks/useZones";
import type { Zone } from "../../api/zones";

/* ── Colour scheme per zone type ── */
const ZONE_COLOURS: Record<string, { bg: string; border: string; label: string }> = {
  intrusion: {
    bg: "rgba(255,60,60,0.18)",
    border: "rgba(255,60,60,0.7)",
    label: "text-red-400",
  },
  loitering: {
    bg: "rgba(255,165,0,0.18)",
    border: "rgba(255,165,0,0.7)",
    label: "text-orange-400",
  },
  crowd: {
    bg: "rgba(255,255,0,0.18)",
    border: "rgba(255,255,0,0.7)",
    label: "text-yellow-400",
  },
};

const DEFAULT_COLOUR = {
  bg: "rgba(43,212,168,0.18)",
  border: "rgba(43,212,168,0.7)",
  label: "text-emerald-400",
};

/* ── Types ── */
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

/* ═══════════════════════════════════════════════════════════════ */
/*  ZoneEditor                                                    */
/* ═══════════════════════════════════════════════════════════════ */
const ZoneEditor: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { zones, addZone, removeZone } = useZones();

  /* Drawing state — refs to avoid re-renders during drag */
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawMode, setDrawMode] = useState(false);
  const [zoneType, setZoneType] = useState("intrusion");
  const drawRef = useRef<Rect | null>(null);
  const previewRef = useRef<HTMLDivElement>(null);

  /* Drag / resize state (also ref-based) */
  const dragRef = useRef<DragState | null>(null);
  const [, forceUpdate] = useState(0);

  /* ── Drawing handlers ── */
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!drawMode || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;
      drawRef.current = { x, y, w: 0, h: 0 };
      setIsDrawing(true);
    },
    [drawMode],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();

      /* ---------- Drawing ---------- */
      if (isDrawing && drawRef.current) {
        const cx = (e.clientX - rect.left) / rect.width;
        const cy = (e.clientY - rect.top) / rect.height;
        drawRef.current.w = cx - drawRef.current.x;
        drawRef.current.h = cy - drawRef.current.y;
        /* Update preview div directly — no React state during drag */
        if (previewRef.current) {
          const d = drawRef.current;
          const left = Math.min(d.x, d.x + d.w) * 100;
          const top = Math.min(d.y, d.y + d.h) * 100;
          const width = Math.abs(d.w) * 100;
          const height = Math.abs(d.h) * 100;
          const s = previewRef.current.style;
          s.left = `${left}%`;
          s.top = `${top}%`;
          s.width = `${width}%`;
          s.height = `${height}%`;
          s.display = "block";
        }
        return;
      }

      /* ---------- Drag / resize ---------- */
      if (dragRef.current) {
        const ds = dragRef.current;
        const dx = (e.clientX - rect.left) / rect.width - ds.startX;
        const dy = (e.clientY - rect.top) / rect.height - ds.startY;

        const zone = zones.find((z) => z.id === ds.zoneId);
        if (!zone) return;

        let nx = zone.x,
          ny = zone.y,
          nw = zone.width,
          nh = zone.height;

        if (ds.type === "move") {
          nx = Math.max(0, Math.min(1 - ds.origW, ds.origX + dx));
          ny = Math.max(0, Math.min(1 - ds.origH, ds.origY + dy));
          nw = ds.origW;
          nh = ds.origH;
        } else {
          // Corner resize
          let x1 = ds.origX,
            y1 = ds.origY,
            x2 = ds.origX + ds.origW,
            y2 = ds.origY + ds.origH;
          if (ds.type.includes("w")) x1 = Math.max(0, ds.origX + dx);
          if (ds.type.includes("e")) x2 = Math.min(1, ds.origX + ds.origW + dx);
          if (ds.type.includes("n")) y1 = Math.max(0, ds.origY + dy);
          if (ds.type.includes("s")) y2 = Math.min(1, ds.origY + ds.origH + dy);
          nx = Math.min(x1, x2);
          ny = Math.min(y1, y2);
          nw = Math.abs(x2 - x1);
          nh = Math.abs(y2 - y1);
        }

        // Mutate directly (live preview), persist on mouseup
        (zone as any).x = nx;
        (zone as any).y = ny;
        (zone as any).width = nw;
        (zone as any).height = nh;
        forceUpdate((n) => n + 1);
      }
    },
    [isDrawing, zones],
  );

  const handleMouseUp = useCallback(() => {
    /* ---------- Finish drawing ---------- */
    if (isDrawing && drawRef.current) {
      const d = drawRef.current;
      const x = Math.min(d.x, d.x + d.w);
      const y = Math.min(d.y, d.y + d.h);
      const w = Math.abs(d.w);
      const h = Math.abs(d.h);
      // Only save zones with meaningful size
      if (w > 0.01 && h > 0.01) {
        addZone({ type: zoneType, x, y, width: w, height: h });
      }
      drawRef.current = null;
      if (previewRef.current) previewRef.current.style.display = "none";
      setIsDrawing(false);
      setDrawMode(false);
      return;
    }

    /* ---------- Finish drag / resize ---------- */
    if (dragRef.current) {
      const zone = zones.find((z) => z.id === dragRef.current!.zoneId);
      if (zone) {
        // Re-save with updated coords (delete + create)
        const { type, x, y, width, height, name } = zone;
        removeZone(zone.id);
        addZone({ type, x, y, width, height, name: name ?? undefined });
      }
      dragRef.current = null;
    }
  }, [isDrawing, zoneType, addZone, removeZone, zones]);

  /* Cleanup on unmount */
  useEffect(() => {
    const up = () => handleMouseUp();
    window.addEventListener("mouseup", up);
    return () => window.removeEventListener("mouseup", up);
  }, [handleMouseUp]);

  /* ── Start drag / resize ── */
  const startDrag = useCallback(
    (e: React.MouseEvent, zone: Zone, type: DragState["type"]) => {
      e.stopPropagation();
      e.preventDefault();
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      dragRef.current = {
        type,
        zoneId: zone.id,
        startX: (e.clientX - rect.left) / rect.width,
        startY: (e.clientY - rect.top) / rect.height,
        origX: zone.x,
        origY: zone.y,
        origW: zone.width,
        origH: zone.height,
      };
    },
    [],
  );

  const handleClearAll = useCallback(() => {
    zones.forEach((z) => removeZone(z.id));
  }, [zones, removeZone]);

  /* ── Colour helper ── */
  const c = (type: string) => ZONE_COLOURS[type] ?? DEFAULT_COLOUR;

  const cursorClass = drawMode ? "cursor-crosshair" : "cursor-default";

  return (
    <div
      ref={containerRef}
      className={`absolute inset-0 z-10 ${cursorClass}`}
      style={{ pointerEvents: drawMode || dragRef.current ? "auto" : "none" }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {/* ── Rendered zones ── */}
      {zones.map((zone) => {
        const col = c(zone.type);
        return (
          <div
            key={zone.id}
            className="absolute group"
            style={{
              left: `${zone.x * 100}%`,
              top: `${zone.y * 100}%`,
              width: `${zone.width * 100}%`,
              height: `${zone.height * 100}%`,
              background: col.bg,
              border: `2px solid ${col.border}`,
              boxShadow: `0 0 12px ${col.border}`,
              pointerEvents: "auto",
            }}
            onMouseDown={(e) => !drawMode && startDrag(e, zone, "move")}
          >
            {/* Label */}
            <span
              className={`absolute top-0.5 left-1 text-[10px] font-mono uppercase tracking-wider select-none ${col.label}`}
            >
              {zone.name ?? zone.type}
            </span>

            {/* Delete button */}
            <button
              className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-red-600/80 text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer pointer-events-auto z-20"
              onClick={(e) => {
                e.stopPropagation();
                removeZone(zone.id);
              }}
            >
              ×
            </button>

            {/* 4 corner resize handles */}
            {(["nw", "ne", "sw", "se"] as const).map((corner) => {
              const pos: React.CSSProperties = {};
              if (corner.includes("n")) pos.top = -4;
              if (corner.includes("s")) pos.bottom = -4;
              if (corner.includes("w")) pos.left = -4;
              if (corner.includes("e")) pos.right = -4;
              const cursorMap = { nw: "nwse-resize", ne: "nesw-resize", sw: "nesw-resize", se: "nwse-resize" };
              return (
                <div
                  key={corner}
                  className="absolute w-2.5 h-2.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity pointer-events-auto z-20"
                  style={{
                    ...pos,
                    background: col.border,
                    cursor: cursorMap[corner],
                  }}
                  onMouseDown={(e) => !drawMode && startDrag(e, zone, corner)}
                />
              );
            })}
          </div>
        );
      })}

      {/* ── Preview rect while drawing ── */}
      <div
        ref={previewRef}
        className="absolute border-2 border-dashed pointer-events-none"
        style={{
          display: "none",
          borderColor: c(zoneType).border,
          background: c(zoneType).bg,
        }}
      />

      {/* ── Controls ── */}
      <div
        className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 rounded-xl bg-ow-bg/80 backdrop-blur-lg border border-white/10 shadow-lg z-30"
        style={{ pointerEvents: "auto" }}
      >
        <button
          onClick={() => setDrawMode((d) => !d)}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all ${
            drawMode
              ? "bg-ow-teal text-ow-bg shadow-[0_0_12px_rgba(43,212,168,0.4)]"
              : "bg-white/5 text-ow-mist/70 hover:bg-white/10"
          }`}
        >
          {drawMode ? "Drawing…" : "Draw Zone"}
        </button>

        <select
          value={zoneType}
          onChange={(e) => setZoneType(e.target.value)}
          className="px-2 py-1.5 rounded-lg text-xs bg-white/5 text-ow-mist/80 border border-white/10 outline-none cursor-pointer appearance-none"
        >
          <option value="intrusion">🔴 Intrusion</option>
          <option value="loitering">🟠 Loitering</option>
          <option value="crowd">🟡 Crowd</option>
        </select>

        {zones.length > 0 && (
          <button
            onClick={handleClearAll}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider bg-red-600/20 text-red-400 hover:bg-red-600/30 transition-all"
          >
            Clear All
          </button>
        )}
      </div>
    </div>
  );
};

export default React.memo(ZoneEditor);
