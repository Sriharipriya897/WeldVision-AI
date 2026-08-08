import React, { useState, useEffect } from 'react';
import { ShieldCheck, Cpu, Clock, Zap } from 'lucide-react';

export default function Header() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const timeStr = time.toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
  });
  const dateStr = time.toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric'
  });

  const weldingDefects = [
    'Crack', 'Porosity', 'Undercut', 'Overlap', 'Lack of Fusion', 'Lack of Penetration',
    'Slag Inclusion', 'Burn Through', 'Excess Reinforcement', 'Underfill', 'Spatter',
    'Blow Hole', 'Misalignment', 'Surface Crack', 'Root Crack', 'Weld Bead Irregularity'
  ];

  return (
    <header
      style={{
        background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 60%, #0F172A 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
      }}
      className="sticky top-0 z-40 shadow-xl"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">

        {/* ── Left: Logo + Branding ────────────────────────────────────── */}
        <div className="flex items-center gap-3.5">
          {/* Logo Icon */}
          <div className="relative">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-lg"
              style={{ background: 'linear-gradient(135deg, #2563EB, #F97316)' }}
            >
              <Zap className="w-5.5 h-5.5 fill-current stroke-[2.2]" style={{ width: 22, height: 22 }} />
            </div>
            {/* Glow ring */}
            <div
              className="absolute inset-0 rounded-xl opacity-30"
              style={{ boxShadow: '0 0 16px 4px rgba(249,115,22,0.6)' }}
            />
          </div>

          {/* Brand Text */}
          <div>
            <div className="flex items-center gap-2.5">
              <h1
                className="text-xl font-bold tracking-tight text-white num-display"
                style={{ letterSpacing: '-0.01em' }}
              >
                WeldVision<span style={{ color: '#F97316' }}>.AI</span>
              </h1>
              <span
                className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-widest"
                style={{
                  background: 'rgba(249,115,22,0.15)',
                  color: '#FDBA74',
                  border: '1px solid rgba(249,115,22,0.3)',
                }}
              >
                Welding Pro v2.0
              </span>
            </div>
            <div className="flex items-center gap-2 mt-0.5 hidden sm:flex">
              <p className="text-[10px] font-medium" style={{ color: '#94A3B8' }}>
                AI-Powered Industrial Welding Inspection &amp; Weld Defect Analysis Platform
              </p>
              <span style={{ color: '#334155' }}>·</span>
              <span className="text-[10px]" style={{ color: '#64748B' }}>AWS D1.1</span>
              <span style={{ color: '#334155' }}>·</span>
              <span className="text-[10px]" style={{ color: '#64748B' }}>ISO 5817</span>
            </div>
          </div>
        </div>

        {/* ── Right: Status + Clock ────────────────────────────────────── */}
        <div className="flex items-center gap-3">

          {/* Real-time clock */}
          <div
            className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            <Clock className="w-3.5 h-3.5" style={{ color: '#64748B' }} />
            <span
              className="text-xs font-medium num-display"
              style={{ color: '#94A3B8', letterSpacing: '0.04em' }}
            >
              {dateStr}  {timeStr}
            </span>
          </div>

          {/* Engine Status */}
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
            style={{
              background: 'rgba(16,185,129,0.1)',
              border: '1px solid rgba(16,185,129,0.25)',
            }}
          >
            <span
              className="w-2 h-2 rounded-full animate-ping"
              style={{ background: '#10B981' }}
            />
            <span className="text-xs font-semibold hidden md:inline" style={{ color: '#34D399' }}>
              Weld Quality Engine Active
            </span>
            <span className="text-xs font-semibold md:hidden" style={{ color: '#34D399' }}>
              Ready
            </span>
          </div>
        </div>

      </div>

      {/* Sub-header stripe showing detectable welding defects */}
      <div
        className="border-t overflow-hidden"
        style={{ borderColor: 'rgba(255,255,255,0.04)', background: 'rgba(0,0,0,0.22)' }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-7 flex items-center gap-5 overflow-x-auto no-scrollbar">
          <span className="text-[10px] font-bold uppercase tracking-wider text-amber-500 whitespace-nowrap">
            Detectable Weld Defects:
          </span>
          {weldingDefects.map((item) => (
            <span
              key={item}
              className="text-[10px] font-medium whitespace-nowrap"
              style={{ color: '#64748B' }}
            >
              {item}
            </span>
          ))}
        </div>
      </div>
    </header>
  );
}
