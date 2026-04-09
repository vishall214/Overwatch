export const threatColorClasses = {
  CRITICAL: "border-threat-critical text-threat-critical",
  HIGH: "border-threat-high text-threat-high",
  MEDIUM: "border-threat-medium text-threat-medium",
  LOW: "border-threat-low text-threat-low"
} as const;

export const threatBorderClasses = {
  CRITICAL: "border-threat-critical",
  HIGH: "border-threat-high",
  MEDIUM: "border-threat-medium",
  LOW: "border-threat-low"
} as const;

export const threatTextClasses = {
  CRITICAL: "text-threat-critical",
  HIGH: "text-threat-high",
  MEDIUM: "text-threat-medium",
  LOW: "text-threat-low"
} as const;

export const threatBadgeBgClasses = {
  CRITICAL: "bg-threat-critical/10",
  HIGH: "bg-threat-high/10",
  MEDIUM: "bg-threat-medium/10",
  LOW: "bg-threat-low/10"
} as const;

export const threatFillClasses = {
  CRITICAL: "bg-threat-critical",
  HIGH: "bg-threat-high",
  MEDIUM: "bg-threat-medium",
  LOW: "bg-threat-low"
} as const;

export const threatGlowClasses = {
  CRITICAL: "shadow-[0_0_8px_rgba(255,0,0,0.3)]",
  HIGH: "shadow-[0_0_8px_rgba(255,140,0,0.3)]",
  MEDIUM: "shadow-[0_0_8px_rgba(255,215,0,0.28)]",
  LOW: "shadow-[0_0_8px_rgba(0,200,90,0.25)]"
} as const;
