import React, { useState, useRef } from 'react';
import {
  Upload, Camera, Play, FileImage, X, Zap,
  ShieldAlert, ScanLine, CheckCircle, ArrowRight, Sparkles
} from 'lucide-react';

const WELD_DEFECT_TAGS = [
  { label: 'Crack',              color: '#EF4444' },
  { label: 'Porosity',           color: '#F59E0B' },
  { label: 'Undercut',           color: '#F97316' },
  { label: 'Overlap',            color: '#F59E0B' },
  { label: 'Lack of Fusion',     color: '#F97316' },
  { label: 'Lack of Penetration',color: '#EF4444' },
  { label: 'Slag Inclusion',     color: '#F59E0B' },
  { label: 'Burn Through',       color: '#EF4444' },
  { label: 'Excess Reinforcement',color: '#10B981' },
  { label: 'Underfill',          color: '#F59E0B' },
  { label: 'Spatter',            color: '#10B981' },
  { label: 'Blow Hole',          color: '#F97316' },
  { label: 'Misalignment',       color: '#F97316' },
  { label: 'Surface Crack',      color: '#EF4444' },
  { label: 'Root Crack',         color: '#EF4444' },
  { label: 'Weld Bead Irregularity', color: '#10B981' },
];

const FEATURES = [
  { icon: Zap,          label: 'Weld Defect AI',      desc: 'Detects 20+ weld joint defect types' },
  { icon: ScanLine,     label: 'CAD Annotation',      desc: 'Non-overlapping callout leader arrows' },
  { icon: ShieldAlert,  label: 'Quality Score & Meter',desc: 'Scorecard, meters & risk analysis' },
  { icon: FileImage,    label: 'Industrial PDF',       desc: 'AWS & ISO compliant report export' },
];

export default function UploadBox({ onImageSelected, selectedImage, onStartInspection, onOpenCamera }) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const processFile = (file) => {
    if (!file.type.startsWith('image/')) {
      alert('Please select a valid welding image file (JPG, PNG, WEBP).');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      onImageSelected({
        file,
        previewUrl: e.target.result,
        name: file.name,
        size: (file.size / (1024 * 1024)).toFixed(2) + ' MB',
      });
    };
    reader.readAsDataURL(file);
  };

  // Helper to load sample weld preset image
  const loadPresetWeld = async (sampleName) => {
    try {
      const response = await fetch('/api/inspect'); // verify host connection if needed
    } catch(e) {}
    
    // Create synthetic weld image canvas for preset test
    const canvas = document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 500;
    const ctx = canvas.getContext('2d');

    // Steel base
    ctx.fillStyle = '#94A3B8';
    ctx.fillRect(0, 0, 800, 500);

    // Heat Affected Zone (HAZ)
    ctx.fillStyle = '#64748B';
    ctx.fillRect(50, 180, 700, 140);

    // Weld bead pass ripples
    ctx.fillStyle = '#CBD5E1';
    for(let x = 60; x < 740; x += 22) {
      ctx.beginPath();
      ctx.ellipse(x, 250, 16, 45, 0, 0, 2 * Math.PI);
      ctx.fill();
      ctx.strokeStyle = '#475569';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    if (sampleName === 'crack') {
      ctx.strokeStyle = '#0F172A';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(250, 246);
      ctx.lineTo(310, 252);
      ctx.lineTo(360, 248);
      ctx.lineTo(420, 256);
      ctx.stroke();
    } else if (sampleName === 'porosity') {
      ctx.fillStyle = '#0F172A';
      const pits = [[450,230,6], [470,240,8], [485,225,5], [460,260,7], [500,245,6]];
      pits.forEach(([x,y,r]) => {
        ctx.beginPath();
        ctx.arc(x,y,r,0,2*Math.PI);
        ctx.fill();
      });
    }

    const dataUrl = canvas.toDataURL('image/jpeg');
    const blob = await (await fetch(dataUrl)).blob();
    const file = new File([blob], `${sampleName}_weld_inspection.jpg`, { type: 'image/jpeg' });

    onImageSelected({
      file,
      previewUrl: dataUrl,
      name: `${sampleName.toUpperCase()} Weld Joint Sample.jpg`,
      size: '0.45 MB',
    });
  };

  const handleFileChange  = (e) => { const f = e.target.files?.[0]; if (f) processFile(f); };
  const handleDragOver    = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave   = ()  => setIsDragging(false);
  const handleDrop        = (e) => {
    e.preventDefault(); setIsDragging(false);
    const f = e.dataTransfer.files?.[0]; if (f) processFile(f);
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">

      {/* ── Hero Title ──────────────────────────────────────────────────────── */}
      <div className="text-center mb-8 animate-fade-up">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold mb-4"
          style={{ background: 'rgba(249,115,22,0.1)', color: '#F97316', border: '1px solid rgba(249,115,22,0.25)' }}>
          <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse inline-block" />
          AI-Powered Industrial Welding Quality &amp; Defect Analysis Platform
        </div>
        <h2 className="text-4xl font-black text-slate-900 tracking-tight leading-none mb-3">
          WeldVision <span style={{
            background: 'linear-gradient(135deg, #2563EB, #F97316)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>AI</span>
        </h2>
        <p className="text-slate-500 text-base font-medium max-w-xl mx-auto">
          Upload welded joint photos, weld bead captures, or shop-floor weld inspections to analyze defects, generate engineering callouts, evaluate quality scores, and export PDF inspection reports.
        </p>
      </div>

      {/* ── Feature Highlights ──────────────────────────────────────────────── */}
      {!selectedImage && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6 animate-fade-up animate-fade-up-delay-1">
          {FEATURES.map(({ icon: Icon, label, desc }) => (
            <div key={label}
              className="bg-white rounded-xl border border-slate-200 p-3.5 card-shadow text-center card-shadow-hover cursor-default">
              <div className="w-9 h-9 rounded-lg bg-orange-50 flex items-center justify-center mx-auto mb-2">
                <Icon className="w-4.5 h-4.5 text-orange-600" style={{ width: 18, height: 18 }} />
              </div>
              <p className="text-xs font-bold text-slate-800">{label}</p>
              <p className="text-[10px] text-slate-400 mt-0.5 leading-tight">{desc}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Main Drop Zone ──────────────────────────────────────────────────── */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`bg-white rounded-2xl card-shadow transition-all duration-300 p-6 sm:p-10
          ${isDragging ? 'drop-zone-active scale-[1.01]' : ''}
          ${!selectedImage ? 'border-2 border-dashed border-slate-200 hover:border-orange-400' : 'border border-slate-200'}
        `}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/*"
          className="hidden"
        />

        {!selectedImage ? (
          /* ── Empty Upload State ─────────────────────────────────────── */
          <div className="py-4 flex flex-col items-center animate-fade-up">

            {/* Upload Icon */}
            <div className="relative mb-6">
              <div
                className="w-20 h-20 rounded-2xl flex items-center justify-center"
                style={{ background: 'linear-gradient(135deg, #FFF7ED, #FFEDD5)' }}
              >
                <Upload className="w-9 h-9 text-orange-600" />
              </div>
              <div
                className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-orange-600 flex items-center justify-center shadow-md text-white font-black text-[10px]"
              >
                +
              </div>
            </div>

            <h3 className="text-xl font-bold text-slate-800 mb-2">
              Upload or capture a welding joint image
            </h3>
            <p className="text-sm text-slate-400 text-center max-w-sm mb-6">
              Supports high-resolution PNG, JPG, JPEG, WEBP weld bead, joint seam, or fillet weld photos.
            </p>

            {/* Quick Demo Weld Samples */}
            <div className="flex items-center gap-2 mb-6">
              <span className="text-xs font-semibold text-slate-400 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-orange-500" /> Try Sample:
              </span>
              <button
                type="button"
                onClick={() => loadPresetWeld('crack')}
                className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-orange-50 text-orange-700 hover:bg-orange-100 border border-orange-200 transition-colors"
              >
                Crack Defect
              </button>
              <button
                type="button"
                onClick={() => loadPresetWeld('porosity')}
                className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors"
              >
                Porosity Defect
              </button>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center justify-center gap-3 w-full max-w-md">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex-1 min-w-[150px] inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl font-bold text-sm text-white transition-all duration-200 shadow-lg cursor-pointer"
                style={{
                  background: 'linear-gradient(135deg, #F97316, #EA580C)',
                  boxShadow: '0 4px 20px -2px rgba(249,115,22,0.4)',
                }}
              >
                <FileImage className="w-4 h-4" />
                Upload Weld Image
              </button>

              <button
                type="button"
                onClick={onOpenCamera}
                className="flex-1 min-w-[150px] inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-sm text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 transition-all duration-200 cursor-pointer"
              >
                <Camera className="w-4 h-4 text-slate-600" />
                Open Camera
              </button>
            </div>

            <p className="text-[11px] text-slate-400 mt-4">
              or drag &amp; drop your welding photo anywhere inside this area
            </p>
          </div>

        ) : (
          /* ── Selected Image Preview State ───────────────────────────── */
          <div className="space-y-5 animate-fade-up">

            {/* Image Preview */}
            <div className="relative group rounded-xl overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center"
              style={{ minHeight: 280, maxHeight: 400 }}>
              <img
                src={selectedImage.previewUrl}
                alt="Selected welding joint"
                className="max-h-96 w-auto object-contain rounded-lg"
              />

              {/* Overlay on hover */}
              <div className="absolute inset-0 bg-slate-900/0 group-hover:bg-slate-900/20 transition-all duration-200 rounded-xl" />

              {/* Remove button */}
              <button
                onClick={() => onImageSelected(null)}
                className="absolute top-3 right-3 w-9 h-9 rounded-full flex items-center justify-center text-white transition-all duration-200 opacity-0 group-hover:opacity-100"
                style={{ background: 'rgba(15,23,42,0.85)' }}
                title="Remove image"
              >
                <X className="w-4 h-4" />
              </button>

              {/* Status badge */}
              <div className="absolute bottom-3 left-3 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-white"
                style={{ background: 'rgba(15,23,42,0.80)', backdropFilter: 'blur(8px)' }}>
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                Weld Image Ready for Inspection
              </div>
            </div>

            {/* File Info Bar */}
            <div className="flex items-center justify-between bg-slate-50 px-4 py-3 rounded-xl border border-slate-200">
              <div className="flex items-center gap-3 overflow-hidden">
                <div className="w-9 h-9 rounded-lg bg-orange-100 flex items-center justify-center shrink-0">
                  <FileImage className="w-4.5 h-4.5 text-orange-600" style={{ width: 18, height: 18 }} />
                </div>
                <div className="overflow-hidden">
                  <p className="text-sm font-semibold text-slate-800 truncate">{selectedImage.name}</p>
                  <p className="text-xs text-slate-400 font-mono">{selectedImage.size}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="text-xs font-semibold text-orange-600 hover:text-orange-800 hover:underline px-2 py-1 transition-colors shrink-0"
              >
                Change
              </button>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center justify-center gap-3 pt-1">
              <button
                type="button"
                onClick={onOpenCamera}
                className="inline-flex items-center gap-2 px-4 py-3 rounded-xl font-semibold text-sm bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200 transition-all cursor-pointer"
              >
                <Camera className="w-4 h-4 text-slate-600" />
                Camera
              </button>

              {/* Start Inspection CTA */}
              <button
                type="button"
                onClick={onStartInspection}
                className="relative flex-1 min-w-[220px] inline-flex items-center justify-center gap-2.5 px-8 py-4 rounded-xl font-black text-base text-white transition-all duration-200 cursor-pointer"
                style={{
                  background: 'linear-gradient(135deg, #F97316 0%, #EA580C 50%, #C2410C 100%)',
                  boxShadow: '0 6px 28px -4px rgba(249,115,22,0.5), 0 2px 8px -1px rgba(249,115,22,0.3)',
                }}
              >
                <Play className="w-5 h-5 fill-current" />
                Start AI Weld Inspection
                <ArrowRight className="w-4 h-4 ml-1 opacity-70" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Detectable Defects Tags ─────────────────────────────────────────── */}
      <div className="mt-6 text-center animate-fade-up animate-fade-up-delay-2">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2.5">
          Detectable Welding Defect Types
        </p>
        <div className="flex flex-wrap items-center justify-center gap-1.5 max-w-3xl mx-auto">
          {WELD_DEFECT_TAGS.map(({ label, color }) => (
            <span
              key={label}
              className="text-xs font-medium px-2.5 py-1 rounded-md bg-white border border-slate-200 card-shadow-sm cursor-default transition-colors hover:border-slate-300"
              style={{ color }}
            >
              {label}
            </span>
          ))}
        </div>
      </div>

    </div>
  );
}
