import React, { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { switchSource, listDemoVideos, uploadVideo, deleteUploadedVideo } from "../api/video";
import { AlertCircle, Check, Loader, Trash2, Upload, Video } from "lucide-react";

interface SourceSelectorProps {
  moduleType: "intrusion" | "loitering" | "crowd";
  onSourceChanged?: () => void;
}

export default function SourceSelector({ moduleType, onSourceChanged }: SourceSelectorProps) {
  const [selectedMode, setSelectedMode] = useState<"demo" | "upload" | "live" | null>(null);
  const [selectedDemo, setSelectedDemo] = useState<string>("");
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadProgress,  setUploadProgress] = useState(0);

  useEffect(() => {
    console.log("UPLOADED STATE:", uploadedFilename);
  }, [uploadedFilename]);

  // Fetch demo videos for this module
  const { data: demoList, isLoading: demoLoading } = useQuery({
    queryKey: ["demoVideos", moduleType],
    queryFn: () => listDemoVideos(moduleType),
    enabled: selectedMode === "demo",
  });

  // Switch source mutation
  const switchMutation = useMutation({
    mutationFn: switchSource,
    onSuccess: () => {
      onSourceChanged?.();
      setSelectedDemo("");
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
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setUploadProgress(0);
      onSourceChanged?.();
    },
  });

  // Handle demo selection
  const handleDemoSelect = async (videoName: string) => {
    setSelectedDemo(videoName);
    try {
      console.log("SWITCH SOURCE:", { type: "demo", module: moduleType, name: videoName });
      await switchMutation.mutateAsync({
        type: "demo",
        module: moduleType,
        name: videoName,
        category: moduleType,
      });
    } catch (error) {
      console.error("Failed to switch to demo:", error);
    }
  };

  // Handle file upload and source switch
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
      console.log("UPLOAD RESPONSE:", uploadResponse);
      setUploadedFilename(uploadResponse.filename);
      setUploadProgress(75);

      console.log("SWITCH SOURCE:", { type: "upload", module: moduleType });
      await switchMutation.mutateAsync({
        type: "upload",
        module: moduleType,
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

  // Handle live camera
  const handleLiveCamera = async () => {
    try {
      console.log("SWITCH SOURCE:", { type: "camera", module: moduleType });
      await switchMutation.mutateAsync({
        type: "camera",
        module: moduleType,
      });
    } catch (error) {
      console.error("Failed to switch to camera:", error);
    }
  };

  return (
    <div className="rounded-2xl glass-panel p-4 mb-4">
      <div className="flex flex-col gap-3">
        <p className="text-sm font-semibold text-ow-mist/70 uppercase tracking-wider">Video Source</p>

        {/* Mode buttons */}
        <div className="grid grid-cols-3 gap-2">
          {/* Demo Mode */}
          <button
            onClick={() => setSelectedMode(selectedMode === "demo" ? null : "demo")}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
              selectedMode === "demo"
                ? "bg-ow-teal/30 border border-ow-teal/50 text-ow-teal/90"
                : "bg-ow-bg/40 border border-[rgba(255,255,255,0.08)] text-ow-mist/70 hover:bg-ow-bg/60"
            }`}
          >
            <Video size={14} />
            Demo
          </button>

          {/* Upload Mode */}
          <button
            onClick={() => setSelectedMode(selectedMode === "upload" ? null : "upload")}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
              selectedMode === "upload"
                ? "bg-ow-teal/30 border border-ow-teal/50 text-ow-teal/90"
                : "bg-ow-bg/40 border border-[rgba(255,255,255,0.08)] text-ow-mist/70 hover:bg-ow-bg/60"
            }`}
          >
            <Upload size={14} />
            Upload
          </button>

          {/* Live Camera */}
          <button
            onClick={handleLiveCamera}
            disabled={switchMutation.isPending}
            className="px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 bg-ow-alert-intrusion/20 border border-ow-alert-intrusion/30 text-ow-alert-intrusion/80 hover:bg-ow-alert-intrusion/30 disabled:opacity-50"
          >
            {switchMutation.isPending ? <Loader size={14} className="animate-spin" /> : <Video size={14} />}
            Live
          </button>
        </div>

        {/* Demo dropdown */}
        {selectedMode === "demo" && (
          <div className="space-y-2">
            {demoLoading ? (
              <div className="text-center py-3">
                <Loader className="w-4 h-4 animate-spin inline text-ow-mist/50" />
              </div>
            ) : demoList?.videos.length ? (
              <select
                value={selectedDemo}
                onChange={(e) => handleDemoSelect(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-ow-bg/40 border border-[rgba(255,255,255,0.12)] text-ow-mist/80 text-sm focus:outline-none focus:border-ow-teal/50"
              >
                <option value="">Select a demo video...</option>
                {demoList.videos.map((video) => (
                  <option key={video} value={video}>
                    {video.replace(".mp4", "").replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-xs text-ow-mist/50">No demo videos available for {moduleType}</p>
            )}
          </div>
        )}

        {/* Upload input */}
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
              className="w-full px-3 py-2 rounded-lg bg-ow-bg/40 border border-dashed border-ow-mist/20 text-ow-mist/60 hover:border-ow-teal/40 hover:text-ow-teal/60 text-sm transition-colors disabled:opacity-50"
            >
              {uploadProgress > 0 ? `Uploading... ${uploadProgress}%` : "Choose Video File"}
            </button>

            {uploadedFilename && (
              <div className="flex items-center justify-between gap-2 rounded-lg border border-[rgba(255,255,255,0.08)] bg-ow-bg/30 px-3 py-2">
                <p className="text-xs text-ow-mist/60 truncate">Uploaded: {uploadedFilename}</p>
                <button
                  onClick={handleDeleteUpload}
                  disabled={deleteUploadMutation.isPending || switchMutation.isPending}
                  className="inline-flex items-center gap-1 rounded-md border border-red-500/30 bg-red-500/10 px-2 py-1 text-[11px] text-red-300 hover:bg-red-500/20 disabled:opacity-50"
                >
                  {deleteUploadMutation.isPending ? <Loader size={12} className="animate-spin" /> : <Trash2 size={12} />}
                  {deleteUploadMutation.isPending ? "Removing..." : "Remove"}
                </button>
              </div>
            )}

            <p className="text-xs text-ow-mist/40">Max 200MB • MP4, AVI</p>
          </div>
        )}

        {/* Status */}
        {switchMutation.error && (
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-ow-alert-intrusion/10 border border-ow-alert-intrusion/20">
            <AlertCircle size={14} className="text-ow-alert-intrusion/60 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-ow-alert-intrusion/60">{(switchMutation.error as Error).message}</p>
          </div>
        )}

        {uploadError && (
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-ow-alert-intrusion/10 border border-ow-alert-intrusion/20">
            <AlertCircle size={14} className="text-ow-alert-intrusion/60 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-ow-alert-intrusion/60">{uploadError}</p>
          </div>
        )}

        {switchMutation.isSuccess && (
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-ow-teal/10 border border-ow-teal/20">
            <Check size={14} className="text-ow-teal/60 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-ow-teal/60">Source switched successfully</p>
          </div>
        )}

        {deleteUploadMutation.error && (
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-ow-alert-intrusion/10 border border-ow-alert-intrusion/20">
            <AlertCircle size={14} className="text-ow-alert-intrusion/60 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-ow-alert-intrusion/60">{(deleteUploadMutation.error as Error).message}</p>
          </div>
        )}

        {deleteUploadMutation.isSuccess && (
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-ow-teal/10 border border-ow-teal/20">
            <Check size={14} className="text-ow-teal/60 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-ow-teal/60">Uploaded video removed</p>
          </div>
        )}
      </div>
    </div>
  );
}
