export type ThreatLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface ThreatInfo {
  score: number;
  level: ThreatLevel;
}

function toRecord(value: unknown): Record<string, unknown> {
  if (typeof value === "object" && value !== null) {
    return value as Record<string, unknown>;
  }
  return {};
}

export function normalizeThreatLevel(level: unknown): ThreatLevel {
  const normalized = String(level ?? "LOW").toUpperCase();
  if (normalized === "CRITICAL") return "CRITICAL";
  if (normalized === "HIGH") return "HIGH";
  if (normalized === "MEDIUM") return "MEDIUM";
  return "LOW";
}

function threatLevelFromScore(score: number): ThreatLevel {
  if (score >= 76) return "CRITICAL";
  if (score >= 51) return "HIGH";
  if (score >= 26) return "MEDIUM";
  return "LOW";
}

export function resolveThreatInfo(alert: {
  threat_score?: unknown;
  threat_level?: unknown;
  metadata?: unknown;
}): ThreatInfo {
  const metadata = toRecord(alert.metadata);
  const rawScore = alert.threat_score ?? metadata.threat_score ?? 0;
  const parsedScore = Number(rawScore);
  const score = Number.isFinite(parsedScore) ? Math.min(100, Math.max(0, Math.round(parsedScore))) : 0;
  const level = threatLevelFromScore(score);

  return { score, level };
}
