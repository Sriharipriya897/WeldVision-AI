import React, { useState, useRef, useEffect } from 'react';
import {
  Download, RotateCcw, AlertTriangle, CheckCircle2, Layers,
  Info, ShieldAlert, Eye, ChevronDown, ChevronUp, Zap,
  TrendingUp, Activity, Target, Shield, Wrench, BookOpen,
  AlertCircle, BarChart3, CircleDot, MapPin, Hash,
  Crosshair, FlaskConical, ClipboardList, Gauge, Star,
  ArrowRight, FileText, Camera, Sparkles, Check
} from 'lucide-react';

// ─── Severity Color & Label Config ─────────────────────────────────────────
// Green = Acceptable (Low), Yellow = Minor (Medium), Orange = Major (High), Red = Critical (Critical)
const SEV = {
  Critical: { bg: '#FEF2F2', text: '#EF4444', border: '#FCA5A5', dot: '#EF4444', hex: '#EF4444', label: 'Critical' },
  High:     { bg: '#FFF7ED', text: '#F97316', border: '#FDBA74', dot: '#F97316', hex: '#F97316', label: 'Major'    },
  Medium:   { bg: '#FFFBEB', text: '#F59E0B', border: '#FCD34D', dot: '#F59E0B', hex: '#F59E0B', label: 'Minor'    },
  Low:      { bg: '#ECFDF5', text: '#10B981', border: '#6EE7B7', dot: '#10B981', hex: '#10B981', label: 'Acceptable' },
};

const ACCEPTANCE_BADGES = {
  "Accepted":             { bg: '#ECFDF5', text: '#059669', border: '#10B981', icon: CheckCircle2 },
  "Accepted With Repair": { bg: '#FFFBEB', text: '#D97706', border: '#F59E0B', icon: AlertTriangle },
  "Requires Rewelding":   { bg: '#FFF7ED', text: '#EA580C', border: '#F97316', icon: AlertCircle },
  "Rejected":             { bg: '#FEF2F2', text: '#DC2626', border: '#EF4444', icon: ShieldAlert },
};

// ─── Reusable Primitives ──────────────────────────────────────────────────
function Card({ children, className = '', style = {} }) {
  return (
    <div
      className={`bg-white rounded-2xl border border-slate-200 card-shadow ${className}`}
      style={style}
    >
      {children}
    </div>
  );
}

function SectionTitle({ icon: Icon, label, right }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-orange-50 flex items-center justify-center">
          <Icon className="w-4 h-4 text-orange-600" />
        </div>
        <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">{label}</h3>
      </div>
      {right && <div>{right}</div>}
    </div>
  );
}

function SeverityBadge({ value, size = 'sm' }) {
  const s = SEV[value] || SEV.Medium;
  const pad = size === 'xs' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';
  return (
    <span
      className={`inline-flex items-center gap-1 ${pad} rounded-full font-bold border`}
      style={{ background: s.bg, color: s.text, borderColor: s.border }}
    >
      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: s.dot }} />
      {s.label}
    </span>
  );
}

// ─── Weld Quality Score Ring ──────────────────────────────────────────────
function ScoreRing({ score }) {
  const r = 54; const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  const dashOff = circ * (1 - pct / 100);
  const color   = pct >= 80 ? '#10B981' : pct >= 60 ? '#F59E0B' : pct >= 45 ? '#F97316' : '#EF4444';

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
        <div className="text-3xl font-black num-display text-slate-900 leading-none">{score}</div>
        <div className="text-xs font-semibold text-slate-400 mt-0.5">/ 100</div>
      </div>
    </div>
  );
}

// ─── Weld Quality Meter (Excellent / Good / Acceptable / Poor / Rejected) ─────
function WeldQualityMeter({ score }) {
  const levels = [
    { label: 'Rejected',  range: [0, 44],   color: '#EF4444' },
    { label: 'Poor',      range: [45, 59],  color: '#F97316' },
    { label: 'Acceptable',range: [60, 74],  color: '#F59E0B' },
    { label: 'Good',      range: [75, 89],  color: '#34D399' },
    { label: 'Excellent', range: [90, 100], color: '#10B981' },
  ];
  const active = levels.find(l => score >= l.range[0] && score <= l.range[1]) || levels[0];
  return (
    <div className="space-y-2">
      <div className="flex gap-1 h-3 rounded-full overflow-hidden">
        {levels.map(l => (
          <div
            key={l.label}
            className="flex-1 rounded-sm transition-all duration-700"
            style={{ background: l.label === active.label ? l.color : '#E2E8F0' }}
          />
        ))}
      </div>
      <div className="flex justify-between text-[9px] font-semibold text-slate-400">
        {levels.map(l => (
          <span key={l.label}
            style={{ color: l.label === active.label ? active.color : undefined,
                     fontWeight: l.label === active.label ? 800 : undefined }}>
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Defect Severity Meter (Low / Moderate / High / Critical) ─────────────────
function DefectSeverityMeter({ riskLabel }) {
  const levels = [
    { label: 'Low',      color: '#10B981' },
    { label: 'Moderate', color: '#F59E0B' },
    { label: 'High',     color: '#F97316' },
    { label: 'Critical', color: '#EF4444' },
  ];
  const activeIdx = levels.findIndex(l => l.label.toLowerCase() === (riskLabel || 'low').toLowerCase());
  return (
    <div className="space-y-2">
      <div className="flex gap-1 h-3 rounded-full overflow-hidden">
        {levels.map((l, i) => (
          <div
            key={l.label}
            className="flex-1 rounded-sm transition-all duration-500"
            style={{ background: i <= activeIdx ? l.color : '#E2E8F0' }}
          />
        ))}
      </div>
      <div className="flex justify-between text-[9px] font-semibold text-slate-400">
        {levels.map(l => (
          <span key={l.label}
            style={{ color: l.label.toLowerCase() === (riskLabel || '').toLowerCase() ? '#1E293B' : undefined,
                     fontWeight: l.label.toLowerCase() === (riskLabel || '').toLowerCase() ? 800 : undefined }}>
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Main Result Component ────────────────────────────────────────────────────
export default function Result({ result, onReset, isDownloadingPdf, onDownloadPdf }) {
  const [activeTab, setActiveTab] = useState('annotated'); // 'original' | 'annotated' | 'overlay'
  const [expandedId, setExpandedId] = useState(null);

  if (!result) return null;

  const defects = result.defects || [];
  const summary = result.summary || {};
  const weldQuality = result.weld_quality || {};

  const totalDefects = summary.total_defects ?? result.total_defects ?? defects.length;
  const criticalCount = summary.critical_defects ?? result.critical_count ?? 0;
  const majorCount = summary.major_defects ?? result.high_count ?? 0;
  const minorCount = summary.minor_defects ?? result.medium_count ?? 0;
  const acceptableCount = summary.acceptable_defects ?? result.low_count ?? 0;

  const score = weldQuality.score ?? result.health_score ?? 90;
  const acceptance = weldQuality.acceptance_status || result.acceptance_status || 'Accepted';
  const condition = weldQuality.condition || result.condition || 'Good';
  const overallRisk = weldQuality.overall_risk || result.overall_risk || 'Low';
  const repairPriority = weldQuality.repair_priority || result.maintenance_status || 'No Action Required';

  const coveragePct = summary.weld_coverage_percent ?? 98.5;
  const defectiveAreaPct = summary.defective_area_percent ?? result.damaged_pct ?? 0.0;
  const confidencePct = summary.inspection_confidence ?? result.inspection_confidence ?? 95.0;

  const verdict = weldQuality.verdict || result.verdict || 'AI Inspection verdict generated.';
  const possibleCauses = weldQuality.possible_causes || [];
  const recommendedActions = weldQuality.recommended_actions || [];

  const largestDefect = summary.largest_defect || result.largest_defect || 'None';
  const dominantDefect = summary.dominant_defect || result.dominant_type || 'None';

  const acceptanceCfg = ACCEPTANCE_BADGES[acceptance] || ACCEPTANCE_BADGES["Accepted"];
  const AcceptanceIcon = acceptanceCfg.icon;

  // Determine current image source based on active view tab
  const getCurrentImage = () => {
    if (activeTab === 'original') return result.original_image;
    if (activeTab === 'overlay') return result.overlay_image || result.annotated_image;
    return result.annotated_image || result.original_image;
  };

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 space-y-6 animate-fade-up">

      {/* ── Top Header Actions ────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 card-shadow">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center">
            <Zap className="w-5 h-5 text-orange-600" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">Weld Inspection Analysis Complete</h2>
            <p className="text-xs text-slate-500 font-medium">
              ID: {result.inspection_time ? `WLD-${result.inspection_time.replace(/[- :]/g, '').slice(0, 14)}` : 'WLD-2026-001'}  ·  AWS D1.1 / ISO 5817 Standard
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-xs text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New Inspection
          </button>

          <button
            type="button"
            onClick={() => onDownloadPdf(result)}
            disabled={isDownloadingPdf}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs text-white transition-all cursor-pointer shadow-md disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #F97316, #EA580C)' }}
          >
            <Download className="w-3.5 h-3.5" />
            {isDownloadingPdf ? 'Generating PDF…' : 'Download Inspection PDF'}
          </button>
        </div>
      </div>

      {/* ── Grid Layout: Image Viewer (Left) + Quality Scorecard (Right) ───── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* ── Left 7 Cols: Multi-View Image Viewer ─────────────────────────── */}
        <div className="lg:col-span-7 space-y-4">
          <Card className="p-4 overflow-hidden">
            {/* View Selector Tabs */}
            <div className="flex items-center justify-between gap-2 pb-3 mb-3 border-b border-slate-100">
              <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
                <button
                  type="button"
                  onClick={() => setActiveTab('original')}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    activeTab === 'original' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <Eye className="w-3.5 h-3.5" />
                  Original Image
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('annotated')}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    activeTab === 'annotated' ? 'bg-white text-orange-600 shadow-sm' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <Crosshair className="w-3.5 h-3.5" />
                  AI Engineering Callout
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('overlay')}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    activeTab === 'overlay' ? 'bg-white text-purple-600 shadow-sm' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  Defect Overlay View
                </button>
              </div>

              <span className="text-[11px] font-semibold text-slate-400 hidden sm:inline">
                Non-Overlapping Engineering Annotations
              </span>
            </div>

            {/* Main Image Display Box */}
            <div className="relative rounded-xl overflow-hidden bg-slate-950 flex items-center justify-center min-h-[380px] max-h-[500px] border border-slate-900">
              <img
                src={getCurrentImage()}
                alt="Weld inspection view"
                className="max-h-[490px] w-auto object-contain"
              />

              {/* Severity Legend overlay at bottom of image view */}
              {activeTab === 'annotated' && (
                <div
                  className="absolute bottom-3 left-3 right-3 flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-xl text-[11px] font-bold text-white"
                  style={{ background: 'rgba(15,23,42,0.85)', backdropFilter: 'blur(8px)' }}
                >
                  <span className="text-slate-300">Callout Severity Legend:</span>
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1 text-red-400"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> Critical</span>
                    <span className="flex items-center gap-1 text-orange-400"><span className="w-2 h-2 rounded-full bg-orange-500 inline-block" /> Major</span>
                    <span className="flex items-center gap-1 text-yellow-400"><span className="w-2 h-2 rounded-full bg-yellow-500 inline-block" /> Minor</span>
                    <span className="flex items-center gap-1 text-emerald-400"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> Acceptable</span>
                  </div>
                </div>
              )}
            </div>

            {/* Quick Caption Bar */}
            <div className="mt-3 text-center text-xs text-slate-500 font-medium">
              {activeTab === 'original' && 'Showing original unprocessed weld seam image capture.'}
              {activeTab === 'annotated' && 'Showing non-overlapping engineering leader-line callouts with severity color coding.'}
              {activeTab === 'overlay' && 'Showing colorized defect overlay highlighting exact void, crack & spatter regions.'}
            </div>
          </Card>
        </div>

        {/* ── Right 5 Cols: Weld Quality & Acceptance Scorecard ─────────────── */}
        <div className="lg:col-span-5 space-y-4">
          <Card className="p-6">
            <div className="text-center pb-4 border-b border-slate-100">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Weld Quality Scorecard
              </span>

              {/* Main Score Ring */}
              <div className="my-4">
                <ScoreRing score={score} />
              </div>

              {/* Acceptance Badge */}
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-black border shadow-sm mb-3"
                style={{ background: acceptanceCfg.bg, color: acceptanceCfg.text, borderColor: acceptanceCfg.border }}>
                <AcceptanceIcon className="w-4 h-4" />
                Status: {acceptance}
              </div>

              <p className="text-xs font-medium text-slate-500">
                Overall Weld Condition: <strong className="text-slate-800">{condition}</strong>
              </p>
            </div>

            {/* Meters Section */}
            <div className="pt-4 space-y-4">
              <div>
                <div className="flex justify-between items-center text-xs font-bold text-slate-700 mb-1.5">
                  <span>Weld Quality Meter</span>
                  <span className="text-orange-600">{score}/100</span>
                </div>
                <WeldQualityMeter score={score} />
              </div>

              <div>
                <div className="flex justify-between items-center text-xs font-bold text-slate-700 mb-1.5">
                  <span>Defect Severity Meter</span>
                  <span className="text-slate-900">{overallRisk}</span>
                </div>
                <DefectSeverityMeter riskLabel={overallRisk} />
              </div>

              {/* Repair Priority Indicator */}
              <div className="pt-2 flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-bold text-slate-700">Repair Priority</span>
                <span className="text-xs font-extrabold px-2.5 py-1 rounded-lg bg-orange-100 text-orange-800 border border-orange-300">
                  {repairPriority}
                </span>
              </div>
            </div>
          </Card>
        </div>

      </div>

      {/* ── Summary Statistics Cards Strip ─────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="p-3.5 text-center">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total Defects</p>
          <p className="text-2xl font-black text-slate-900 mt-1">{totalDefects}</p>
          <p className="text-[10px] text-slate-400 mt-0.5">Identified Regions</p>
        </Card>

        <Card className="p-3.5 text-center bg-red-50/50 border-red-200">
          <p className="text-[10px] font-bold text-red-600 uppercase tracking-wider">Critical Defects</p>
          <p className="text-2xl font-black text-red-600 mt-1">{criticalCount}</p>
          <p className="text-[10px] text-red-400 mt-0.5">Red Code</p>
        </Card>

        <Card className="p-3.5 text-center bg-orange-50/50 border-orange-200">
          <p className="text-[10px] font-bold text-orange-600 uppercase tracking-wider">Major Defects</p>
          <p className="text-2xl font-black text-orange-600 mt-1">{majorCount}</p>
          <p className="text-[10px] text-orange-400 mt-0.5">Orange Code</p>
        </Card>

        <Card className="p-3.5 text-center bg-yellow-50/50 border-yellow-200">
          <p className="text-[10px] font-bold text-yellow-700 uppercase tracking-wider">Minor Defects</p>
          <p className="text-2xl font-black text-yellow-700 mt-1">{minorCount}</p>
          <p className="text-[10px] text-yellow-500 mt-0.5">Yellow Code</p>
        </Card>

        <Card className="p-3.5 text-center">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Defective Area</p>
          <p className="text-2xl font-black text-slate-900 mt-1">{defectiveAreaPct}%</p>
          <p className="text-[10px] text-slate-400 mt-0.5">Of Weld Surface</p>
        </Card>

        <Card className="p-3.5 text-center">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">AI Confidence</p>
          <p className="text-2xl font-black text-blue-600 mt-1">{confidencePct}%</p>
          <p className="text-[10px] text-slate-400 mt-0.5">Precision Rate</p>
        </Card>
      </div>

      {/* ── AI Verdict Narrative + Possible Causes & Actions ──────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Verdict Box (Left 6 Cols) */}
        <div className="lg:col-span-6">
          <Card className="p-6 h-full flex flex-col justify-between">
            <div>
              <SectionTitle icon={FileText} label="AI Inspection Verdict" />
              <div className="p-4 rounded-xl bg-orange-50/60 border border-orange-200 text-slate-800 text-sm leading-relaxed mb-4">
                "{verdict}"
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs text-slate-500 font-medium">
              <span>Dominant Defect: <strong className="text-slate-800">{dominantDefect}</strong></span>
              <span>Largest Feature: <strong className="text-slate-800">{largestDefect}</strong></span>
            </div>
          </Card>
        </div>

        {/* Possible Causes & Repair Actions (Right 6 Cols) */}
        <div className="lg:col-span-6">
          <Card className="p-6 h-full flex flex-col justify-between">
            <div>
              <SectionTitle icon={Wrench} label="Engineering Repair & Causes" />

              <div className="space-y-3">
                {/* Causes */}
                <div>
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-orange-500" /> Possible Causes (AI Estimated)
                  </h4>
                  <ul className="space-y-1 text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200">
                    {possibleCauses.length > 0 ? (
                      possibleCauses.map((cause, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-orange-500 font-bold">•</span>
                          <span>{cause}</span>
                        </li>
                      ))
                    ) : (
                      <li className="text-slate-400 italic">No specific causes identified.</li>
                    )}
                  </ul>
                </div>

                {/* Actions */}
                <div>
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Wrench className="w-3.5 h-3.5 text-emerald-500" /> Recommended Repair Actions
                  </h4>
                  <ul className="space-y-1 text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200">
                    {recommendedActions.length > 0 ? (
                      recommendedActions.map((act, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-emerald-500 font-bold">•</span>
                          <span>{act}</span>
                        </li>
                      ))
                    ) : (
                      <li className="text-slate-400 italic">Zero repair required.</li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          </Card>
        </div>

      </div>

      {/* ── Detailed Defect Table ─────────────────────────────────────────── */}
      <Card className="p-6">
        <SectionTitle
          icon={ClipboardList}
          label={`Detected Weld Defect Catalogue (${defects.length})`}
          right={
            <span className="text-xs text-slate-400 font-semibold">
              Click defect row for engineering repair details
            </span>
          }
        />

        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900 text-white font-bold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-3 px-4">Defect ID</th>
                <th className="py-3 px-4">Defect Name</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">AI Confidence</th>
                <th className="py-3 px-4">Weld Zone Location</th>
                <th className="py-3 px-4">Size (mm)</th>
                <th className="py-3 px-4">Defect Area (%)</th>
                <th className="py-3 px-4">Repair Priority</th>
                <th className="py-3 px-4 text-center">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 font-medium text-slate-700">
              {defects.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400 italic">
                    Zero visual weld defects detected. Weld seam is in excellent sound condition.
                  </td>
                </tr>
              ) : (
                defects.map((d, i) => {
                  const defId = d.id || `WLD-${i + 1}`;
                  const isExpanded = expandedId === defId;
                  return (
                    <React.Fragment key={defId}>
                      <tr
                        onClick={() => setExpandedId(isExpanded ? null : defId)}
                        className={`hover:bg-slate-50 cursor-pointer transition-colors ${
                          isExpanded ? 'bg-orange-50/40' : ''
                        }`}
                      >
                        <td className="py-3.5 px-4 font-black text-slate-900 font-mono">{defId}</td>
                        <td className="py-3.5 px-4 font-bold text-slate-900">{d.type || d.defect_name}</td>
                        <td className="py-3.5 px-4">
                          <SeverityBadge value={d.severity} />
                        </td>
                        <td className="py-3.5 px-4 font-mono">
                          <span className="font-bold text-slate-800">{Math.round((d.confidence || 0) * 100)}%</span>
                          {d.confidence_tier && (
                            <span className={`ml-1.5 px-1.5 py-0.5 rounded text-[9px] font-semibold ${
                              d.confidence >= 0.20 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                              d.confidence >= 0.10 ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                              'bg-amber-50 text-amber-700 border border-amber-200'
                            }`}>
                              {d.confidence_tier}
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-slate-600">{d.location || d.weld_zone || 'Centerline'}</td>
                        <td className="py-3.5 px-4 font-mono">{d.size_mm || 'N/A'}</td>
                        <td className="py-3.5 px-4 font-bold">{d.area_pct}%</td>
                        <td className="py-3.5 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">
                            {d.repair_priority || d.priority || 'Monitor'}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <button type="button" className="text-slate-400 hover:text-slate-700">
                            {isExpanded ? <ChevronUp className="w-4 h-4 mx-auto" /> : <ChevronDown className="w-4 h-4 mx-auto" />}
                          </button>
                        </td>
                      </tr>

                      {/* Expanded Repair Details Dropdown */}
                      {isExpanded && (
                        <tr className="bg-slate-50/80">
                          <td colSpan={8} className="p-4 border-t border-slate-200">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                              <div className="bg-white p-3 rounded-lg border border-slate-200">
                                <h5 className="font-bold text-slate-800 mb-1 text-[11px] uppercase tracking-wider text-orange-600">
                                  Root Cause Analysis:
                                </h5>
                                <p className="text-slate-600 leading-relaxed">
                                  {d.possible_cause || d.root_cause || d.explain || 'Thermal stress or gas entrapped during weld solidifying pass.'}
                                </p>
                              </div>

                              <div className="bg-white p-3 rounded-lg border border-slate-200">
                                <h5 className="font-bold text-slate-800 mb-1 text-[11px] uppercase tracking-wider text-emerald-600">
                                  Recommended Repair Procedure:
                                </h5>
                                <p className="text-slate-600 leading-relaxed">
                                  {d.recommended_repair || d.repair_method || d.action || 'Grind out defect region and re-weld.'}
                                </p>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ── Bottom Download CTA Banner ────────────────────────────────────── */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 card-shadow">
        <div>
          <h3 className="text-base font-bold">Need official industrial documentation?</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Download full multi-page PDF report complete with company logo, inspection ID, visual evidence, defect tables &amp; sign-off block.
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
