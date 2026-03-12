import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { API } from "../api/config";
import { useCameraStatus } from "../hooks/useCameraStatus";

interface CameraStreamContextType {
  imageElement: HTMLImageElement | null;
  cameraOnline: boolean;
}

const CameraStreamContext = createContext<CameraStreamContextType>({
  imageElement: null,
  cameraOnline: false,
});

export const useCameraStream = () => useContext(CameraStreamContext);

export const CameraStreamProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { data: status } = useCameraStatus();
  const cameraOnline = status?.is_running ?? false;
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [imageReady, setImageReady] = useState<HTMLImageElement | null>(null);

  useEffect(() => {
    if (!cameraOnline) {
      if (imgRef.current) {
        imgRef.current.src = "";
        imgRef.current = null;
        setImageReady(null);
      }
      return;
    }

    if (!imgRef.current) {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.src = API.camera.stream;
      imgRef.current = img;
      setImageReady(img);
    }

    // Cleanup when provider unmounts entirely
    return () => {
      if (imgRef.current) {
        imgRef.current.src = "";
        imgRef.current = null;
        setImageReady(null);
      }
    };
  }, [cameraOnline]);

  return (
    <CameraStreamContext.Provider value={{ imageElement: imageReady, cameraOnline }}>
      {children}
    </CameraStreamContext.Provider>
  );
};
