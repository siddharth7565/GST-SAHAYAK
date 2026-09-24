import React from 'react';
import { VerificationSignal, ComparisonResult } from '../../types';
import { formatPercent } from '../../lib/utils';
import { ShieldCheck, ShieldAlert, ShieldX, HelpCircle, Layers, CheckCircle2, FileCode } from 'lucide-react';
import { Progress } from '../ui/progress';
import { Badge } from '../ui/badge';

interface VerificationResultProps {
  verification?: VerificationSignal | null;
  comparison?: ComparisonResult | null;
}

export function VerificationResult({ verification, comparison }: VerificationResultProps) {
  if (!verification) return null;

  const scorePercent = (verification.verification_score * 100);
  const level = verification.verification_level;

  const levelConfigs = {
    HIGH: {
      bg: 'bg-emerald-50/80 border-emerald-300',
      text: 'text-emerald-950',
      badge: 'bg-emerald-600 text-white',
      icon: <ShieldCheck className="h-6 w-6 text-emerald-600" />,
      indicator: 'bg-emerald-500',
    },
    MEDIUM: {
      bg: 'bg-amber-50/80 border-amber-300',
      text: 'text-amber-950',
      badge: 'bg-amber-500 text-white',
      icon: <ShieldAlert className="h-6 w-6 text-amber-600" />,
      indicator: 'bg-amber-500',
    },
    LOW: {
      bg: 'bg-rose-50/80 border-rose-300',
      text: 'text-rose-950',
      badge: 'bg-rose-600 text-white',
      icon: <ShieldX className="h-6 w-6 text-rose-600" />,
      indicator: 'bg-rose-500',
    },
    UNVERIFIED: {
      bg: 'bg-slate-50/80 border-slate-300',
      text: 'text-slate-900',
      badge: 'bg-slate-600 text-white',
      icon: <HelpCircle className="h-6 w-6 text-slate-500" />,
      indicator: 'bg-slate-400',
    },
  };

  const config = levelConfigs[level] || levelConfigs.UNVERIFIED;

  return (
    <div className={`rounded-xl border p-5 shadow-gst-subtle my-5 space-y-4 ${config.bg}`}>
      {/* Top Banner Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-white shadow-2xs">
            {config.icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${config.badge}`}>
                {level} VERIFICATION
              </span>
              <span className="text-xs font-extrabold text-gst-dark capitalize">
                [{verification.verification_status.replace(/_/g, ' ')}]
              </span>
            </div>
            <p className="text-xs text-gst-muted font-medium mt-0.5">
              Deterministic evidence relevance & multi-model consensus signal
            </p>
          </div>
        </div>

        {/* Big Score Gauge */}
        <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-xl border border-gst-border shadow-2xs">
          <div className="text-right">
            <div className="text-2xl font-black text-gst-dark tracking-tight leading-none">
              {formatPercent(verification.verification_score)}
            </div>
            <div className="text-[10px] font-bold uppercase text-gst-muted mt-0.5">Verification Score</div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <Progress value={scorePercent} indicatorClassName={config.indicator} className="h-2.5 bg-white" />
      </div>

      {/* Explanation Quote Box */}
      <div className="bg-white/90 rounded-lg p-3 border border-gst-border/60 text-xs text-gst-dark leading-relaxed flex items-start gap-2">
        <span className="text-gst-orange-deep font-bold shrink-0">💡 Note:</span>
        <span>{verification.explanation}</span>
      </div>

      {/* Component Breakdown Cards & Shared Legal References */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
        <div className="bg-white rounded-lg p-2.5 border border-gst-border/50 text-center">
          <div className="text-[10px] font-bold text-gst-muted uppercase">Evidence Quality</div>
          <div className="text-sm font-black text-gst-dark mt-0.5">
            {formatPercent(verification.components.evidence_component)}
          </div>
        </div>
        <div className="bg-white rounded-lg p-2.5 border border-gst-border/50 text-center">
          <div className="text-[10px] font-bold text-gst-muted uppercase">Model Agreement</div>
          <div className="text-sm font-black text-gst-dark mt-0.5">
            {formatPercent(verification.components.agreement_component)}
          </div>
        </div>
        <div className="bg-white rounded-lg p-2.5 border border-gst-border/50 text-center">
          <div className="text-[10px] font-bold text-gst-muted uppercase">Model Coverage</div>
          <div className="text-sm font-black text-gst-dark mt-0.5">
            {formatPercent(verification.components.model_coverage_component)}
          </div>
        </div>
      </div>

      {/* Shared Legal References Cited */}
      {comparison && comparison.shared_legal_references && comparison.shared_legal_references.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-gst-border/50 text-xs">
          <span className="font-bold text-gst-dark flex items-center gap-1">
            <FileCode className="h-3.5 w-3.5 text-gst-orange-deep" />
            Shared Legal References Cited:
          </span>
          {comparison.shared_legal_references.map((ref) => (
            <span
              key={ref}
              className="px-2 py-0.5 rounded bg-gst-orange-light text-gst-orange-deep font-bold border border-gst-orange/40 text-xs"
            >
              {ref}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
