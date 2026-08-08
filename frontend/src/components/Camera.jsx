import React, { useEffect, useRef, useState } from 'react';
import { Camera as CameraIcon, X, RefreshCw, Check } from 'lucide-react';

export default function Camera({ onCapture, onClose }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [error, setError] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

  const startCamera = async () => {
    setError(null);
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      console.error("Camera access error:", err);
      setError("Unable to access camera. Please allow camera permissions or use image upload.");
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
  };

  const takeSnapshot = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
      setCapturedImage(dataUrl);
    }
  };

  const confirmCapture = () => {
    if (!capturedImage) return;

    // Convert dataURL to File object
    fetch(capturedImage)
      .then(res => res.blob())
      .then(blob => {
        const file = new File([blob], `camera-capture-${Date.now()}.jpg`, { type: 'image/jpeg' });
        onCapture({
          file: file,
          previewUrl: capturedImage,
          name: file.name,
          size: (file.size / (1024 * 1024)).toFixed(2) + ' MB'
        });
        stopCamera();
        onClose();
      });
  };

  const retake = () => {
    setCapturedImage(null);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
      <div className="bg-white rounded-2xl max-w-2xl w-full overflow-hidden shadow-2xl border border-slate-200">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div className="flex items-center space-x-2">
            <CameraIcon className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-bold text-slate-800">Camera Inspection Capture</h3>
          </div>
          <button 
            onClick={() => { stopCamera(); onClose(); }}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Camera Viewport Area */}
        <div className="relative bg-slate-950 aspect-video flex items-center justify-center overflow-hidden">
          {error ? (
            <div className="p-6 text-center text-slate-300">
              <p className="text-red-400 font-semibold mb-2">{error}</p>
              <button 
                onClick={startCamera} 
                className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Retry Camera Access
              </button>
            </div>
          ) : capturedImage ? (
            <img src={capturedImage} alt="Captured" className="w-full h-full object-contain" />
          ) : (
            <video 
              ref={videoRef} 
              autoPlay 
              playsInline 
              muted 
              className="w-full h-full object-contain"
            />
          )}

          {/* Grid overlay lines for engineering alignment */}
          {!capturedImage && !error && (
            <div className="absolute inset-0 pointer-events-none border-2 border-blue-500/20">
              <div className="w-full h-full grid grid-cols-3 grid-rows-3">
                {[...Array(9)].map((_, i) => (
                  <div key={i} className="border border-white/10"></div>
                ))}
              </div>
            </div>
          )}

          <canvas ref={canvasRef} className="hidden" />
        </div>

        {/* Footer Actions */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <p className="text-xs text-slate-500 font-medium">
            Align metal component surface within camera frame.
          </p>

          <div className="flex items-center space-x-3">
            {!capturedImage ? (
              <button
                type="button"
                onClick={takeSnapshot}
                disabled={!!error}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 text-white text-sm font-semibold rounded-xl shadow-md shadow-blue-600/20 transition-colors cursor-pointer"
              >
                <CameraIcon className="w-4 h-4" /> Capture Photo
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={retake}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 text-sm font-semibold rounded-xl transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-4 h-4" /> Retake
                </button>
                <button
                  type="button"
                  onClick={confirmCapture}
                  className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-md transition-colors cursor-pointer"
                >
                  <Check className="w-4 h-4" /> Use Photo
                </button>
              </>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
