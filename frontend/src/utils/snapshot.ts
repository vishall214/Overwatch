import { API } from "../api/config";

export interface SnapshotLike {
  snapshot_path?: string | null;
  snapshot_filename?: string | null;
  snapshot_url?: string | null;
}

export function extractSnapshotFilename(snapshot: SnapshotLike): string {
  const direct = (snapshot.snapshot_filename ?? "").trim();
  if (direct) {
    return direct;
  }

  const rawPath = (snapshot.snapshot_path ?? "").trim();
  if (!rawPath) {
    return "";
  }

  const normalized = rawPath.replace(/\\/g, "/").split("?")[0].split("#")[0];
  const pieces = normalized.split("/").filter(Boolean);
  return pieces.length > 0 ? pieces[pieces.length - 1] : "";
}

export function resolveSnapshotSrc(snapshot: SnapshotLike): string {
  const filename = extractSnapshotFilename(snapshot);
  if (filename) {
    return API.snapshots(filename);
  }

  return (snapshot.snapshot_url ?? "").trim();
}
