import React from 'react';
import { PipelineStage } from '../../types';
import { cn } from '../../lib/utils';
import { Check, Loader2, HelpCircle, Database, FileText, Cpu, GitCompare, ShieldCheck } from 'lucide-react';

interface PipelineStepperProps {
  stage: PipelineStage;
}

interface StepInfo {
  key: string;
  label: string;
  sublabel: string;
  icon: React.ReactNode;
}

const STEPS: StepInfo[] = [
  { key: 'QUESTION', label: 'QUESTION', sublabel: 'Input prompt', icon: <HelpCircle className="h-4 w-4" /> },
  { key: 'RAG', label: 'RAG', sublabel: 'pgvector search', icon: <Database className="h-4 w-4" /> },
  { key: 'EVIDENCE', label: 'EVIDENCE', sublabel: 'Shared context', icon: <FileText className="h-4 w-4" /> },
  { key: 'LLM POOL', label: 'LLM POOL', sublabel: '4 models pool', icon: <Cpu className="h-4 w-4" /> },
  { key: 'COMPARE', label: 'COMPARE', sublabel: 'Agreement test', icon: <GitCompare className="h-4 w-4" /> },
  { key: 'VERIFY', label: 'VERIFY', sublabel: 'Signal score', icon: <ShieldCheck className="h-4 w-4" /> },
];

export function PipelineStepper({ stage }: PipelineStepperProps) {
  // Determine step status based on overall pipeline stage
  const getStepStatus = (index: number): 'completed' | 'active' | 'pending' => {
    if (stage === 'IDLE') return 'pending';
    if (stage === 'COMPLETE') return 'completed';

    const stageOrder: Record<PipelineStage, number> = {
      IDLE: -1,
      RETRIEVING: 1, // Step RAG (1) active
      GENERATING: 3, // Step LLM POOL (3) active
      COMPARING: 4,  // Step COMPARE (4) active
      VERIFYING: 5,  // Step VERIFY (5) active
      COMPLETE: 6,
    };

    const currentActiveIndex = stageOrder[stage] ?? -1;

    if (index < currentActiveIndex) return 'completed';
    if (index === currentActiveIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="w-full bg-white rounded-xl border border-gst-border p-4 shadow-gst-subtle my-4">
      <div className="flex items-center justify-between mb-3 border-b border-gst-border/40 pb-2">
        <div className="text-xs font-extrabold uppercase tracking-wider text-gst-dark flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-gst-orange-deep inline-block" />
          Multi-Model Verification Workflow Pipeline
        </div>
        <div className="text-[11px] font-semibold text-gst-orange-deep bg-gst-orange-verylight px-2.5 py-0.5 rounded-full border border-gst-orange/30">
          {stage === 'IDLE' && 'Ready for Query'}
          {stage === 'RETRIEVING' && 'Retrieving Shared Evidence...'}
          {stage === 'GENERATING' && 'Executing Model Pool...'}
          {stage === 'COMPARING' && 'Comparing Cross-Model Consensus...'}
          {stage === 'VERIFYING' && 'Calculating Verification Score...'}
          {stage === 'COMPLETE' && 'Verification Complete'}
        </div>
      </div>

      {/* Desktop Stepper (Horizontal) */}
      <div className="hidden md:flex items-center justify-between relative px-2">
        {STEPS.map((step, idx) => {
          const status = getStepStatus(idx);
          const isLast = idx === STEPS.length - 1;

          return (
            <React.Fragment key={step.key}>
              {/* Step Node */}
              <div className="flex flex-col items-center relative z-10 text-center">
                <div
                  className={cn(
                    "w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs transition-all duration-300 shadow-2xs border-2",
                    status === 'completed' && "bg-gst-green text-white border-gst-green",
                    status === 'active' && "bg-gst-orange text-gst-dark border-gst-orange-deep animate-pulse ring-4 ring-gst-orange/20",
                    status === 'pending' && "bg-gst-cream text-gst-muted border-gst-border"
                  )}
                >
                  {status === 'completed' ? (
                    <Check className="h-4 w-4 stroke-[3]" />
                  ) : status === 'active' ? (
                    <Loader2 className="h-4 w-4 animate-spin text-gst-dark" />
                  ) : (
                    step.icon
                  )}
                </div>
                <div className="mt-1.5">
                  <div className={cn(
                    "text-xs font-bold tracking-tight",
                    status === 'active' ? "text-gst-orange-deep" : status === 'completed' ? "text-gst-dark" : "text-gst-muted"
                  )}>
                    {step.label}
                  </div>
                  <div className="text-[10px] text-gst-muted font-medium">{step.sublabel}</div>
                </div>
              </div>

              {/* Connecting Line */}
              {!isLast && (
                <div className="flex-1 h-0.5 mx-2 bg-gst-border relative -top-3">
                  <div
                    className="h-full bg-gst-green transition-all duration-500"
                    style={{
                      width: status === 'completed' ? '100%' : '0%',
                    }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Mobile Stepper (Vertical) */}
      <div className="flex md:hidden flex-col space-y-3 px-1 pt-1">
        {STEPS.map((step, idx) => {
          const status = getStepStatus(idx);
          return (
            <div key={step.key} className="flex items-center gap-3">
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs shrink-0 border",
                  status === 'completed' && "bg-gst-green text-white border-gst-green",
                  status === 'active' && "bg-gst-orange text-gst-dark border-gst-orange-deep animate-pulse",
                  status === 'pending' && "bg-gst-cream text-gst-muted border-gst-border"
                )}
              >
                {status === 'completed' ? <Check className="h-3.5 w-3.5 stroke-[3]" /> : step.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-bold text-gst-dark flex items-center justify-between">
                  <span>{step.label}</span>
                  <span className="text-[10px] text-gst-muted font-normal">{step.sublabel}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
