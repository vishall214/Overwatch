import React, { useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { switchSource, listDemoVideos, uploadVideo, deleteUploadedVideo } from "../api/video";
import { AlertCircle, Check, Loader, Trash2, Upload, Video } from "lucide-react";

type SourceModule = "intrusion" | "loitering" | "crowd" | "weapon_detection" | "weapons";
type ApiModule = "intrusion" | "loitering" | "crowd";
type DemoCategory = "intrusion" | "loitering" | "crowd";

interface SourceSelectorProps {
  moduleType: SourceModule;
  onSourceChanged?: () => void;
}

const moduleToApiModuleMap: Record<SourceModule, ApiModule> = {
  intrusion: "intrusion",
  loitering: "loitering",
  crowd: "crowd",
  weapon_detection: "intrusion",
  weapons: "intrusion",
};

const moduleToCategoryMap: Record<SourceModule, DemoCategory> = {
  intrusion: "intrusion",
  loitering: "loitering",
  crowd: "crowd",
  weapon_detection: "intrusion",
  weapons: "intrusion",
};

const moduleToFilenameHintMap: Record<SourceModule, string> = {
  intrusion: "intrusion",
  loitering: "loitering",
  crowd: "crowd",
  weapon_detection: "weapon",
  weapons: "weapon",
};

function formatDemoName(filename: string): string {
  return filename.replace(/\.[^/.]+$/, "").replace(/[_-]+/g, " ").trim();
}

export default function SourceSelector({ moduleType, onSourceChanged }: SourceSelectorProps) {
  const [selectedMode, setSelectedMode] = useState<"demo" | "upload" | "live" | null>(null);
  const [selectedDemo, setSelectedDemo] = useState<string>("");
  const [loadedDemo, setLoadedDemo] = useState<string>("");
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const apiModule = moduleToApiModuleMap[moduleType];
  const demoCategory = moduleToCategoryMap[moduleType];
  const demoFilenameHint = moduleToFilenameHintMap[moduleType].toLowerCase();

  const { data: demoList, isLoading: demoLoading } = useQuery({
    queryKey: ["demoVideos", demoCategory],
    queryFn: () => listDemoVideos(demoCategory),
    enabled: selectedMode === "demo",
  });

  const filteredDemoVideos = useMemo(() => {
    const videos = demoList?.videos ?? [];
    return videos.filter((video) => video.toLowerCase().includes(demoFilenameHint));
  }, [demoFilenameHint, demoList?.videos]);

  const switchMutation = useMutation({
    mutationFn: switchSource,
    onSuccess: () => {
      onSourceChanged?.();
      setUploadProgress(0);
    },
  });

  const deleteUploadMutation = useMutation({
    mutationFn: (filename: string) => deleteUploadedVideo(filename),
    onSuccess: () => {
      setUploadedFilename(null);
      setUploadError(null);
      setSelectedMode(null);
      setSelectedDemo("");
      setLoadedDemo("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setUploadProgress(0);
      onSourceChanged?.();
    },
  });

  const handleDemoSelect = async (videoName: string) => {
    setSelectedDemo(videoName);
    try {
      await switchMutation.mutateAsync({
        type: "demo",
        module: apiModule,
        name: videoName,
        category: demoCategory,
      });
      setLoadedDemo(videoName);
    } catch (error) {
      console.error("Failed to switch to demo:", error);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      if (file.size > 200 * 1024 * 1024) {
        throw new Error("File too large. Max allowed size is 200MB.");
      }

      setUploadError(null);
      setUploadProgress(50);
      const uploadResponse = await uploadVideo(file);
      setUploadedFilename(uploadResponse.filename);
      setUploadProgress(75);

      await switchMutation.mutateAsync({
        type: "upload",
        module: apiModule,
        path: uploadResponse.path,
      });
      setUploadProgress(100);
    } catch (error) {
      console.error("Failed to upload video:", error);
      setUploadProgress(0);
      setUploadError((error as Error).message || "Failed to upload video");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDeleteUpload = async () => {
    if (!uploadedFilename) return;

    try {
      await deleteUploadMutation.mutateAsync(uploadedFilename);
    } catch (error) {
      console.error("Failed to delete uploaded video:", error);
    }
  };

  const handleLiveCamera = async () => {
    try {
      await switchMutation.mutateAsync({
        type: "camera",
        module: apiModule,
      });
      setLoadedDemo("");
    } catch (error) {
      console.error("Failed to switch to camera:", error);
    }
  };

  return (
    <div className="glass rounded-xl p-3 h-full">
      <div className="flex flex-col gap-3">
        <p className="text-sm font-semibold text-textSecondary uppercase tracking-wider">Video Source</p>

        {/* Mode buttons */}
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={() => setSelectedMode(selectedMode === "demo" ? null : "demo")}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
              selectedMode === "demo"
                ? "bg-card border border-accent/40 text-textPrimary"
                : "bg-surface border border-border text-textSecondary hover:text-textPrimary"
            }`}
          >
            <Video size={14} />
            Demo
          </button>

          <button
            onClick={() => setSelectedMode(selectedMode === "upload" ? null : "upload")}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
              selectedMode === "upload"
                ? "bg-card border border-accent/40 text-textPrimary"
                : "bg-surface border border-border text-textSecondary hover:text-textPrimary"
            }`}
          >
            <Upload size={14} />
            Upload
          </button>

          <button
            onClick={handleLiveCamera}
            disabled={switchMutation.isPending}
            className="px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 bg-accent/20 border border-accent/40 text-accent hover:bg-accent/30 disabled:opacity-50"
          >
            {switchMutation.isPending ? <Loader size={14} className="animate-spin" /> : <Video size={14} />}
            Live
          </button>
        </div>

        {selectedMode === "demo" && (
          <div className="space-y-2">
            {demoLoading ? (
              <div className="text-center py-3">
                <Loader className="w-4 h-4 animate-spin inline text-textMuted" />
              </div>
            ) : filteredDemoVideos.length ? (
              <div className="max-h-36 overflow-y-auto space-y-1">
                {filteredDemoVideos.map((video) => {
                  const isSelected = selectedDemo === video;
                  return (
                    <button
                      key={video}
                      type="button"
                      onClick={() => void handleDemoSelect(video)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                        isSelected
                          ? "bg-teal-500/20 border border-teal-400 text-white"
                          : "bg-surface border border-border text-textSecondary hover:text-textPrimary"
                      }`}
                    >
                      [{` ${formatDemoName(video)} `}]
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-textSecondary">No demo videos available for {moduleType}</p>
            )}

            {loadedDemo ? (
              <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-accent/10 border border-accent/30">
                <Check size={14} className="text-accent mt-0.5 flex-shrink-0" />
                <p className="text-xs text-accent">Demo loaded: {formatDemoName(loadedDemo)}</p>
              </div>
            ) : null}
          </div>
        )}

        {selectedMode === "upload" && (
          <div className="space-y-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.avi"
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => {
                if (fileInputRef.current) {
                  fileInputRef.current.value = "";
                  fileInputRef.current.click();
                }
              }}
              disabled={switchMutation.isPending || deleteUploadMutation.isPending || uploadProgress > 0}
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border text-textSecondary hover:text-textPrimary text-sm transition-colors disabled:opacity-50"
            >
              {uploadProgress > 0 ? `Uploading... ${uploadProgress}%` : "Choose Video File"}
            </button>

            {uploadedFilename && (
              <div className="flex items-center justify-between gap-2 rounded-lg bg-surface border border-border px-3 py-2">
                <p className="text-xs text-textSecondary truncate">Uploaded: {uploadedFilename}</p>
                <button
                  onClick={handleDeleteUpload}
                  disabled={deleteUploadMutation.isPending || switchMutation.isPending}
                  className="inline-flex items-center gap-1 rounded-md bg-threat-critical/15 border border-threat-critical/30 px-2 py-1 text-[11px] text-threat-critical hover:bg-threat-critical/25 disabled:opacity-50"
                >
                  {deleteUploadMutation.isPending ? <Loader size={12} className="animate-spin" /> : <Trash2 size={12} />}
                  {deleteUploadMutation.isPending ? "Removing..." : "Remove"}
                </button>
              </div>
            )}

            <p className="text-xs text-textMuted">Max 200MB • MP4, AVI</p>
          </div>
        )}

        {switchMutation.error && (
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-threat-critical/10 border border-threat-critical/30">
            <AlertCircle size={14} className="text-threat-critical mt-0.5 flex-shrink-0" />
            <p className="text-xs text-threat-critical">{(switchMutation.error as Error).message}</p>
          </div>
        )}

        {uploadError && (
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-threat-critical/10 border border-threat-critical/30">
            <AlertCircle size={14} className="text-threat-critical mt-0.5 flex-shrink-0" />
            <p className="text-xs text-threat-critical">{uploadError}</p>
          </div>
        )}

        {deleteUploadMutation.error && (
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-threat-critical/10 border border-threat-critical/30">
            <AlertCircle size={14} className="text-threat-critical mt-0.5 flex-shrink-0" />
            <p className="text-xs text-threat-critical">{(deleteUploadMutation.error as Error).message}</p>
          </div>
        )}

        {deleteUploadMutation.isSuccess && (
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-accent/10 border border-accent/30">
            <Check size={14} className="text-accent mt-0.5 flex-shrink-0" />
            <p className="text-xs text-accent">Uploaded video removed</p>
          </div>
        )}
      </div>
    </div>
  );
}
