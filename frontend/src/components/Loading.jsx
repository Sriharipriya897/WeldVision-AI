import React, { useEffect, useState } from 'react';
import { Cpu, Search, Scan, FileCheck, CheckCircle2, Loader2, Zap } from 'lucide-react';

const STEPS = [
  {
    title: 'Uploading Weld Seam Capture',
    desc: 'Transferring high-resolution welding joint image to WeldVision AI',
    icon: Scan,
    color: '#3B82F6',
  },
  {
    title: 'Scanning Weld Seam & HAZ',
    desc: 'Analyzing weld bead profile, root pass boundaries, and heat-affected zone',
    icon: Search,
    color: '#F59E0B',
  },
  {
    title: 'Detecting Weld Defects',
    desc: 'Evaluating Cracks, Porosity, Undercut, Fusion, and 20+ defect types',
    icon: Zap,
    color: '#F97316',
  },
  {
    title: 'Computing Quality & PDF Report',
    desc: 'Calculating Weld Quality Score, Acceptance Status, and PDF Report',
    icon: FileCheck,
    color: '#10B981',
  },
];

export default function Loading() {
  const [stepIdx, setStepIdx]   = useState(0);
  const [subPct, setSubPct]     = useState(0);

  useEffect(() => {
    const stepTimer = setInterval(() => {
      setStepIdx(p => (p < STEPS.length - 1 ? p + 1 : p));
      setSubPct(0);
    }, 950);

    const pctTimer = setInterval(() => {
      setSubPct(p => Math.min(p + 4, 100));
    }, 35);

    return () => { clearInterval(stepTimer); clearInterval(pctTimer); };
  }, []);

  const step    = STEPS[stepIdx];
  const Icon    = step.icon;
  const overall = Math.round((stepIdx / STEPS.length) * 100 + subPct / STEPS.length);

  return (
    <div className="max-w-lg mx-auto py-12 px-4 animate-fade-up">
      <div
        className="rounded-2xl overflow-hidden card-shadow"
        style={{ background: '#FFFFFF', border: '1px solid #E2E8F0' }}
      >

        {/* ── Gradient top strip ──────────────────────────────────────────── */}
        <div
          className="h-1.5"
          style={{
            background: `linear-gradient(90deg, ${step.color} ${overall}%, #E2E8F0 ${overall}%)`,
            transition: 'background 0.3s ease',
          }}
        />

        <div className="p-8 space-y-7">

          {/* ── Central Spinner + Icon ──────────────────────────────────── */}
          <div className="flex flex-col items-center gap-5">
            <div className="relative w-28 h-28 flex items-center justify-center">
              {/* Outer spinning ring */}
              <svg
                className="absolute inset-0 w-full h-full"
                viewBox="0 0 112 112"
                style={{ animation: 'spin 1.2s linear infinite' }}
              >
                <circle
                  cx="56" cy="56" r="50"
                  fill="none" stroke="#E2E8F0" strokeWidth="4"
                />
                <circle
                  cx="56" cy="56" r="50"
                  fill="none" stroke={step.color} strokeWidth="4"
                  strokeDasharray={`${2 * Math.PI * 50 * overall / 100} ${2 * Math.PI * 50 * (1 - overall / 100)}`}
                  strokeLinecap="round"
                  style={{ transform: 'rotate(-90deg)', transformOrigin: '56px 56px', transition: 'stroke-dasharray 0.3s ease' }}
                />
              </svg>

              {/* Inner icon circle */}
              <div
                className="w-18 h-18 rounded-2xl flex items-center justify-center"
                style={{
                  width: 68, height: 68,
                  background: `linear-gradient(135deg, ${step.color}18, ${step.color}10)`,
                  border: `1.5px solid ${step.color}30`,
                }}
              >
                <Icon
                  style={{ width: 32, height: 32, color: step.color, animation: 'pulse 1.5s ease-in-out infinite' }}
                />
              </div>
            </div>

            {/* Step text */}
            <div className="text-center">
              <h3
                className="text-xl font-black text-slate-900 tracking-tight num-display mb-1"
                key={stepIdx}
                style={{ animation: 'fadeSlideUp 0.35s ease both' }}
              >
                {step.title}…
              </h3>
              <p
                className="text-sm text-slate-400 max-w-xs leading-relaxed"
                key={stepIdx + 'desc'}
                style={{ animation: 'fadeSlideUp 0.35s 0.08s ease both' }}
              >
                {step.desc}
              </p>
            </div>
          </div>

          {/* ── Step Pills ────────────────────────────────────────────────── */}
          <div className="grid grid-cols-4 gap-2">
            {STEPS.map((s, i) => {
              const done    = i < stepIdx;
              const current = i === stepIdx;
              const SIcon   = s.icon;
              return (
                <div key={i} className="flex flex-col items-center gap-1.5">
                  <div
                    className="w-full h-1.5 rounded-full transition-all duration-500"
                    style={{
                      background: done ? s.color : current ? `${s.color}80` : '#E2E8F0',
                    }}
                  />
                  <div className="flex items-center gap-1">
                    {done
                      ? <CheckCircle2 style={{ width: 12, height: 12, color: s.color }} />
                      : <SIcon style={{ width: 12, height: 12, color: current ? s.color : '#CBD5E1' }} />
                    }
                    <span
                      className="text-[9px] font-semibold"
                      style={{ color: current ? s.color : done ? '#64748B' : '#CBD5E1' }}
                    >
                      Step {i + 1}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* ── Overall Progress + Percentage ─────────────────────────────── */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-1.5">
                <Loader2
                  className="animate-spin"
                  style={{ width: 13, height: 13, color: '#94A3B8' }}
                />
                <span className="text-xs text-slate-400 font-medium">Scanning Weld Bead…</span>
              </div>
              <span
                className="text-sm font-black num-display"
                style={{ color: step.color }}
              >
                {Math.min(overall, 99)}%
              </span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${Math.min(overall, 99)}%`,
                  background: `linear-gradient(90deg, ${step.color}CC, ${step.color})`,
                }}
              />
            </div>
          </div>

          {/* ── Footer note ───────────────────────────────────────────────── */}
          <p className="text-[10px] text-slate-400 text-center">
            Evaluating weld joint integrity against AWS D1.1 and ISO 5817 standards
          </p>

        </div>
      </div>
    </div>
  );
}
