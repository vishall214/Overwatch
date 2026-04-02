import { API } from "./config";
import { getAuthHeaders } from "./auth";

export interface SourceSwitchRequest {
  type: "camera" | "demo" | "upload";
  name?: string;
  category?: string;
  path?: string;
}

export interface SourceSwitchResponse {
  success: boolean;
  message: string;
  source_type: string;
  source_path: string | null;
}

export interface DemoVideoList {
  videos: string[];
  category: string;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  filename: string;
  path: string;
  size_mb: number;
}

export interface SourceInfo {
  type: string;
  path: string;
  source_name: string;
  is_open: boolean;
  is_capturing: boolean;
}

/**
 * Switch the active video source.
 */
export async function switchSource(request: SourceSwitchRequest): Promise<SourceSwitchResponse> {
  const res = await fetch(API.video.source, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to switch source");
  }

  return res.json();
}

/**
 * List available demo videos for a category.
 */
export async function listDemoVideos(category: string): Promise<DemoVideoList> {
  const res = await fetch(API.video.demoList(category));

  if (!res.ok) {
    throw new Error("Failed to list demo videos");
  }

  return res.json();
}

/**
 * Upload a video file.
 */
export async function uploadVideo(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(API.video.upload, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to upload video");
  }

  return res.json();
}

/**
 * Get current source information.
 */
export async function getSourceInfo(): Promise<SourceInfo> {
  const res = await fetch(API.video.sourceInfo);

  if (!res.ok) {
    throw new Error("Failed to get source info");
  }

  return res.json();
}
