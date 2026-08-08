import React, { useState } from 'react';
import Header from './components/Header';
import UploadBox from './components/UploadBox';
import Camera from './components/Camera';
import Loading from './components/Loading';
import Result from './components/Result';
import { AlertCircle } from 'lucide-react';

export default function App() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [status, setStatus] = useState('idle'); // 'idle' | 'analyzing' | 'result' | 'error'
  const [inspectionResult, setInspectionResult] = useState(null);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleImageSelected = (imageObj) => {
    setSelectedImage(imageObj);
    setErrorMessage(null);
    if (!imageObj) {
      setStatus('idle');
      setInspectionResult(null);
    }
  };

  const startInspection = async () => {
    if (!selectedImage || !selectedImage.file) return;

    setStatus('analyzing');
    setErrorMessage(null);

    const formData = new FormData();
    formData.append('file', selectedImage.file);

    try {
      const response = await fetch('/api/inspect', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Welding inspection failed. Please try again.');
      }

      const data = await response.json();
      
      // Smooth transition delay for loading animation
      setTimeout(() => {
        setInspectionResult(data);
        setStatus('result');
      }, 1200);

    } catch (err) {
      console.error("Inspection request error:", err);
      setErrorMessage(err.message || 'Failed to connect to WeldVision backend inspection server.');
      setStatus('error');
    }
  };

  const handleDownloadPdf = async (resultData) => {
    const payload = resultData || inspectionResult;
    if (!payload) return;
    setIsDownloadingPdf(true);

    try {
      const response = await fetch('/api/download-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Failed to generate PDF report.');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `WeldVision_Inspection_Report_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("PDF download error:", err);
      alert('Error downloading PDF report. Please try again.');
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const handleReset = () => {
    setSelectedImage(null);
    setInspectionResult(null);
    setStatus('idle');
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Industrial Header */}
      <Header />

      {/* Main Content Area */}
      <main className="flex-1 pb-16">
        
        {/* Error Alert Message */}
        {errorMessage && (
          <div className="max-w-3xl mx-auto mt-6 px-4">
            <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl flex items-center justify-between text-sm">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
                <span>{errorMessage}</span>
              </div>
              <button 
                onClick={() => setStatus('idle')} 
                className="font-bold underline text-xs text-red-800 hover:text-red-950"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Workflow State Renderer */}
        {status === 'idle' && (
          <UploadBox
            selectedImage={selectedImage}
            onImageSelected={handleImageSelected}
            onStartInspection={startInspection}
            onOpenCamera={() => setIsCameraOpen(true)}
          />
        )}

        {status === 'analyzing' && (
          <Loading />
        )}

        {(status === 'result' || status === 'error') && inspectionResult && (
          <Result
            result={inspectionResult}
            onDownloadPdf={handleDownloadPdf}
            isDownloadingPdf={isDownloadingPdf}
            onReset={handleReset}
          />
        )}

        {/* WebRTC Live Camera Modal */}
        {isCameraOpen && (
          <Camera
            onCapture={(capturedImageObj) => {
              handleImageSelected(capturedImageObj);
              setIsCameraOpen(false);
            }}
            onClose={() => setIsCameraOpen(false)}
          />
        )}

      </main>

      {/* Industrial Footer */}
      <footer
        className="border-t py-5 text-center"
        style={{
          background: '#0F172A',
          borderColor: 'rgba(255,255,255,0.06)',
        }}
      >
        <p className="text-xs font-medium text-slate-400">
          WeldVision AI © 2026 — AI-Powered Industrial Welding Quality &amp; Weld Defect Analysis Platform
        </p>
        <div className="flex items-center justify-center gap-3 mt-1.5">
          {['AWS D1.1 / D1.2', 'ISO 5817', 'EN 1090-2', 'ASME Sec VIII'].map(s => (
            <span key={s} className="text-[10px] font-medium text-slate-600">{s}</span>
          ))}
        </div>
      </footer>
    </div>
  );
}
