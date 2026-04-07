export function normalizeEventType(eventType: string): string {
  return eventType === "dangerous_object" ? "weapon_detected" : eventType;
}

export function isWeaponEventType(eventType: string): boolean {
  const normalized = normalizeEventType(eventType);
  return normalized === "weapon_detected" || normalized === "weapon_in_zone";
}

export function formatEventLabel(eventType: string): string {
  const normalized = normalizeEventType(eventType);
  if (normalized === "weapon_in_zone") return "Weapon In Zone";
  if (normalized === "weapon_detected") return "Weapon Detected";
  return normalized.replace(/_/g, " ");
}
