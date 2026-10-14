import React, { useState } from 'react';
import {
  Download, RotateCcw, AlertTriangle, CheckCircle2, Layers,
  Info, ShieldAlert, Eye, ChevronDown, ChevronUp, Zap,
  Activity, Target, Shield, Wrench, BookOpen,
  AlertCircle, BarChart3, MapPin, Hash,
  Crosshair, FileText, Check, Calendar, Clock,
  Cpu, FileCheck, HelpCircle, Search, AlertOctagon, CheckCircle
} from 'lucide-react';

// ─── Severity Color & Label Config ─────────────────────────────────────────
const SEV = {
  Critical: { bg: '#FEF2F2', text: '#DC2626', border: '#FCA5A5', dot: '#DC2626', label: 'Critical' },
  High:     { bg: '#FFF7ED', text: '#EA580C', border: '#FDBA74', dot: '#EA580C', label: 'High'     },
  Medium:   { bg: '#FFFBEB', text: '#D97706', border: '#FCD34D', dot: '#D97706', label: 'Medium'   },
  Low:      { bg: '#ECFDF5', text: '#059669', border: '#6EE7B7', dot: '#059669', label: 'Low'      },
  "Review Required": { bg: '#FFF7ED', text: '#EA580C', border: '#FDBA74', dot: '#EA580C', label: 'Review Required' },
};

const STATUS_BADGES = {
  "Excellent":            { bg: '#ECFDF5', text: '#047857', border: '#10B981', icon: CheckCircle2 },
  "Accepted":             { bg: '#ECFDF5', text: '#047857', border: '#10B981', icon: CheckCircle2 },
  "Accepted With Repair": { bg: '#FFFBEB', text: '#B45309', border: '#F59E0B', icon: AlertTriangle },
  "Requires Repair":      { bg: '#FFF7ED', text: '#C2410C', border: '#F97316', icon: AlertCircle },
  "Requires Rewelding":   { bg: '#FFF7ED', text: '#C2410C', border: '#F97316', icon: AlertCircle },
  "Rejected":             { bg: '#FEF2F2', text: '#B91C1C', border: '#EF4444', icon: ShieldAlert },
  "No Target Defect Detected": { bg: '#ECFDF5', text: '#047857', border: '#10B981', icon: CheckCircle2 },
};



function cleanText(val) {
  if (!val) return '';
  let s = String(val);
  s = s.replace(/^svg[-_ ]*/gi, '')
       .replace(/^svg([A-Z])/i, '$1')
       .replace(/\bsvg\b/gi, '')
       .replace(/\s+/g, ' ')
       .trim();
  return s;
}

function Card({ children, className = '', style = {} }) {
  return (
    <div className={`bg-white rounded-2xl border border-slate-200 shadow-sm ${className}`} style={style}>
      {children}
    </div>
  );
}

function SectionTitle({ icon: Icon, label, right }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-xl bg-orange-50 flex items-center justify-center border border-orange-200/60">
          <Icon className="w-4 h-4 text-orange-600" />
        </div>
        <h3 className="text-sm font-extrabold text-slate-800 uppercase tracking-wider">{label}</h3>
      </div>
      {right && <div>{right}</div>}
    </div>
  );
}

function ScoreRing({ score }) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  const dashOff = circ * (1 - pct / 100);
  const color = pct >= 80 ? '#10B981' : pct >= 65 ? '#F59E0B' : pct >= 45 ? '#F97316' : '#EF4444';

  return (
    <div className="relative w-36 h-36 flex items-center justify-center mx-auto">
      <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 124 124">
        <circle cx="62" cy="62" r={r} fill="none" stroke="#F1F5F9" strokeWidth="10" />
        <circle
          cx="62" cy="62" r={r} fill="none" stroke={color} strokeWidth="10"
          strokeDasharray={circ} strokeDashoffset={dashOff}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1.4s cubic-bezier(0.22,1,0.36,1)' }}
        />
      </svg>
      <div className="relative text-center">
        <div className="text-3xl font-black text-slate-900 leading-none">{score}</div>
        <div className="text-xs font-semibold text-slate-400 mt-1">/ 100</div>
      </div>
    </div>
  );
}

export default function Result({ result, onReset, isDownloadingPdf, onDownloadPdf }) {
  const [activeTab, setActiveTab] = useState('annotated');

  if (!result) return null;

  const defects = result.defects || [];
  const summary = result.summary || {};
  const weldQuality = result.weld_quality || {};
  const qa = result.quality_assessment || {};

  const totalDetectedIndications = result.total_detected_indications ?? defects.length;
  const score = qa.score ?? weldQuality.score ?? result.health_score ?? 98;
  const status = qa.status ?? weldQuality.overall_status ?? weldQuality.acceptance_status ?? result.acceptance_status ?? 'Accepted';
  const overallSeverity = qa.severity ?? weldQuality.overall_severity ?? weldQuality.overall_risk ?? result.overall_risk ?? 'Low';

  const inspectionDate = result.inspection_date || new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  const inspectionTime = result.inspection_time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const inspectionId = result.inspection_id || `WLD-${Date.now()}`;
  const fileName = result.file_name || 'weld_specimen.jpg';

  const statusCfg = STATUS_BADGES[status] || STATUS_BADGES["Accepted"];
  const StatusIcon = statusCfg.icon;

  // Extract only the actual detected defect cards from result
  const detectedCards = (result.twelve_class_inspection || []).filter(
    card => card.category === 'detected' || card.status_type === 'detected' || (card.status && card.status.includes('DETECTED')) || (card.count && card.count > 0)
  );

  const getCurrentImage = () => {
    if (activeTab === 'original') return result.original_image;
    if (activeTab === 'overlay') return result.overlay_image || result.annotated_image;
    return result.annotated_image || result.original_image;
  };

  const scrollToImage = () => {
    setActiveTab('annotated');
    const el = document.getElementById('image-viewer-card');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 space-y-6">

      {/* ── System Header & Navigation Bar ───────────────────────────────── */}
      <div className="bg-slate-900 text-white p-6 rounded-2xl shadow-xl flex flex-wrap items-center justify-between gap-4 border border-slate-800">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-xl bg-orange-500/20 border border-orange-500/40 flex items-center justify-center text-orange-400">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black tracking-tight text-white">WELDVISION AI</h1>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-orange-500/20 text-orange-400 border border-orange-500/30 uppercase tracking-wide">
                AI Visual Inspection
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium mt-0.5">
              AI-Assisted Weld Quality Inspection & 12-Class Discontinuity Screening
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-all cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New Inspection
          </button>

          <button
            type="button"
            onClick={() => onDownloadPdf(result)}
            disabled={isDownloadingPdf}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs text-white transition-all cursor-pointer shadow-lg disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #F97316, #EA580C)' }}
          >
            <Download className="w-3.5 h-3.5" />
            {isDownloadingPdf ? 'Generating PDF…' : 'Download Inspection PDF'}
          </button>
        </div>
      </div>

      {/* ── SECTION 1: OVERALL INSPECTION RESULT ─────────────────────────── */}
      <Card className="p-6">
        <SectionTitle icon={Activity} label="Overall Inspection Result" />

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Quality Score */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 text-center flex flex-col justify-center">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Quality Score</span>
            <ScoreRing score={score} />
            <span className="text-xs font-semibold text-slate-500 mt-2">AI Visual Screening Metric</span>
          </div>

          {/* Overall Status */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 text-center flex flex-col justify-center items-center">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Overall Status</span>
            <div
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl text-sm font-extrabold border shadow-xs"
              style={{ background: statusCfg.bg, color: statusCfg.text, borderColor: statusCfg.border }}
            >
              <StatusIcon className="w-4 h-4" />
              {status}
            </div>
            <p className="text-xs text-slate-500 font-medium mt-3">
              Screening Classification per AWS D1.1 Reference Criteria
            </p>
          </div>

          {/* Overall Severity */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 text-center flex flex-col justify-center items-center">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Overall Severity</span>
            <div className={`px-4 py-2 rounded-2xl text-sm font-extrabold border ${
              overallSeverity === 'Critical' ? 'bg-red-50 text-red-700 border-red-200' :
              overallSeverity === 'High' ? 'bg-orange-50 text-orange-700 border-orange-200' :
              overallSeverity === 'Medium' ? 'bg-amber-50 text-amber-700 border-amber-200' :
              'bg-emerald-50 text-emerald-700 border-emerald-200'
            }`}>
              {overallSeverity}
            </div>
            <p className="text-xs text-slate-500 font-medium mt-3">
              Discontinuity Impact Assessment
            </p>
          </div>

          {/* Total Detected Indications */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 text-center flex flex-col justify-center items-center">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Total Detected Indications</span>
            <div className={`text-4xl font-black ${totalDetectedIndications > 0 ? 'text-orange-600' : 'text-emerald-600'}`}>
              {totalDetectedIndications}
            </div>
            <p className="text-xs text-slate-500 font-medium mt-2">
              {totalDetectedIndications > 0 ? 'Actual YOLO Discontinuity Predictions' : 'Zero Defect Indications Detected'}
            </p>
          </div>
        </div>
      </Card>

      {/* ── Visual Inspection Viewer ──────────────────────────────────────── */}
      <Card id="image-viewer-card" className="p-5">
        <div className="flex items-center justify-between gap-2 pb-3 mb-3 border-b border-slate-100">
          <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => setActiveTab('original')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'original' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Original Image
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('annotated')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'annotated' ? 'bg-white text-orange-600 shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <Crosshair className="w-3.5 h-3.5" />
              Annotated Inspection Image
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('overlay')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'overlay' ? 'bg-white text-purple-600 shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Heatmap Overlay
            </button>
          </div>

          <span className="text-xs font-medium text-slate-400 hidden sm:inline">
            YOLO11 Segmentation Leader-Line View
          </span>
        </div>

        <div className="relative rounded-xl overflow-hidden bg-slate-950 flex items-center justify-center min-h-[380px] max-h-[520px] border border-slate-900">
          <img
            src={getCurrentImage()}
            alt="Weld inspection view"
            className="max-h-[510px] w-auto object-contain"
          />
        </div>
      </Card>

      {/* ── SECTION 3: DETECTED WELD DEFECTS ───────────────────── */}
      <Card className="p-6">
        <SectionTitle
          icon={ShieldAlert}
          label={totalDetectedIndications > 0 ? `Detected Weld Defects (${totalDetectedIndications})` : "Defect Detection Results"}
          right={
            <span className="text-xs text-slate-400 font-semibold">
              {totalDetectedIndications > 0 ? `${detectedCards.length} Defect Categor${detectedCards.length > 1 ? 'ies' : 'y'} Identified` : '12 Defect Categories Checked'}
            </span>
          }
        />

        {totalDetectedIndications === 0 || detectedCards.length === 0 ? (
          <div className="p-8 rounded-2xl bg-emerald-50/70 border border-emerald-200/80 text-center space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-emerald-100 border border-emerald-200 flex items-center justify-center text-emerald-600 mx-auto shadow-xs">
              <CheckCircle className="w-8 h-8" />
            </div>
            <h4 className="text-lg font-black text-emerald-900 tracking-tight">
              No Target Defects Detected
            </h4>
            <p className="text-xs text-emerald-700 max-w-xl mx-auto leading-relaxed font-medium">
              YOLO11 visual screening evaluated the specimen across all 12 supported welding defect categories (Slag Inclusion, Undercut, Porosity, Incomplete Fusion, Overlap, Underfill, Spatter, Excessive Convexity, Excessive Concavity, Excessive Weld Reinforcement, Incomplete Penetration, Excessive Penetration). Zero defect indications met or exceeded the detection threshold.
            </p>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-bold bg-white text-emerald-800 border border-emerald-300">
              Total Filtered Defect Count: 0
            </div>
          </div>
        ) : (
          <>
            <p className="text-xs text-slate-500 mb-6 font-medium">
              Displaying only defects confirmed by YOLO11 segmentation passing the confidence threshold and deduplication filtering.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {detectedCards.map((card, idx) => {
                return (
                  <div
                    key={card.class_name || idx}
                    className="p-4 rounded-xl border transition-all space-y-3 bg-red-50/40 border-red-200 hover:border-red-300"
                  >
                    {/* Card Top Row */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-lg bg-red-100 text-red-800 text-[11px] font-black flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        <h4 className="text-sm font-extrabold text-slate-900">{card.class_name}</h4>
                      </div>

                      <span className="px-2.5 py-1 rounded-full text-[11px] font-extrabold bg-red-100 text-red-800 border border-red-300 inline-flex items-center gap-1.5 shrink-0">
                        <AlertOctagon className="w-3.5 h-3.5 text-red-600" />
                        {card.status || 'DETECTED'}
                      </span>
                    </div>

                    {/* Detected Details Pills */}
                    <div className="flex flex-wrap gap-2 pt-1">
                      <span className="px-2 py-0.5 rounded-md bg-white border border-red-200 text-red-700 text-[10px] font-bold">
                        Confidence: {card.confidence}%
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-white border border-red-200 text-red-700 text-[10px] font-bold">
                        Count: {card.count} indication(s)
                      </span>
                      {card.location && (
                        <span className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 text-[10px] font-bold">
                          {card.location}
                        </span>
                      )}
                      {card.severity && (
                        <span className="px-2 py-0.5 rounded-md bg-orange-100 border border-orange-300 text-orange-800 text-[10px] font-extrabold">
                          Severity: {card.severity}
                        </span>
                      )}
                    </div>

                    {/* Observation / Details Text */}
                    <div className="text-xs space-y-1.5 pt-1">
                      {card.observation && (
                        <p className="text-red-950 font-semibold bg-white/80 p-2 rounded-lg border border-red-100">
                          <strong className="text-red-700 uppercase tracking-wider text-[10px] block">Observation:</strong>
                          {card.observation}
                        </p>
                      )}

                      {card.explanation && (
                        <p className="text-slate-600 leading-relaxed font-medium">
                          <strong className="text-slate-700 font-bold block text-[10px] uppercase tracking-wider">Explanation:</strong>
                          {card.explanation}
                        </p>
                      )}

                      {card.possible_causes && (
                        <p className="text-slate-600 leading-relaxed">
                          <strong className="text-orange-700 font-bold block text-[10px] uppercase tracking-wider">Possible Causes:</strong>
                          {card.possible_causes}
                        </p>
                      )}

                      {card.recommendation && (
                        <p className="text-slate-600 leading-relaxed font-medium">
                          <strong className="text-emerald-700 font-bold block text-[10px] uppercase tracking-wider">Recommendation:</strong>
                          {card.recommendation}
                        </p>
                      )}
                    </div>

                    {/* Action button */}
                    <div className="pt-2 flex justify-end">
                      <button
                        type="button"
                        onClick={scrollToImage}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-orange-700 bg-orange-100 hover:bg-orange-200 border border-orange-300 transition-colors cursor-pointer"
                      >
                        <Crosshair className="w-3.5 h-3.5" />
                        View Detection on Image
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </Card>

      {/* ── Quality Assessment Rationale ──────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <SectionTitle icon={HelpCircle} label="Quality Assessment Rationale" />
          <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 text-slate-800 text-xs leading-relaxed space-y-2">
            <p className="font-bold text-slate-900">
              Assigned Score: <strong className="text-blue-700">{score}/100</strong>  ·  Overall Severity: <strong className="text-slate-900">{overallSeverity}</strong>
            </p>
            <p className="text-slate-700">
              {qa.explanation || result.quality_assessment?.explanation || 'Quality score dynamically computed from YOLO segmentation outputs and visual inspection rules.'}
            </p>
          </div>
          <div className="mt-3 text-[11px] text-slate-400 font-medium">
            Standard: AWS D1.1 Table 6.1 (Visual Inspection Acceptance Criteria)
          </div>
        </Card>

        <Card className="p-6">
          <SectionTitle icon={Shield} label="Final Inspection Conclusion" />
          <div
            className="p-4 rounded-xl text-xs leading-relaxed border space-y-2"
            style={{ background: statusCfg.bg, borderColor: statusCfg.border, color: statusCfg.text }}
          >
            <p className="font-black text-sm uppercase">
              Verdict: {status}
            </p>
            <p className="font-medium text-slate-800">
              {result.conclusion || weldQuality.conclusion || 'AI Inspection completed. Perform qualified inspector review as required.'}
            </p>
          </div>
          <div className="mt-3 flex justify-between text-[11px] text-slate-500 font-medium">
            <span>Status: <strong className="text-slate-800">{status}</strong></span>
            <span>Repair Priority: <strong className="text-slate-800">{weldQuality.repair_priority || 'No Action Required'}</strong></span>
          </div>
        </Card>
      </div>

      {/* ── PDF Export Banner ─────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 shadow-xl border border-slate-800">
        <div>
          <h3 className="text-base font-bold">Official Industrial Inspection Documentation</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Download full PDF report with complete 12-class inspection summary, genuine YOLO visual callouts, and inspector sign-off block.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onDownloadPdf(result)}
          disabled={isDownloadingPdf}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm text-white transition-all cursor-pointer shadow-lg disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #F97316, #EA580C)' }}
        >
          <Download className="w-4 h-4" />
          {isDownloadingPdf ? 'Generating PDF…' : 'Export Full PDF Report'}
        </button>
      </div>

    </div>
  );
}
