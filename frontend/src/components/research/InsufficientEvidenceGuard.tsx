import React from 'react';
import { AlertCircle, ShieldOff, RefreshCw } from 'lucide-react';
import { Button } from '../ui/button';

interface InsufficientEvidenceGuardProps {
  onRetryWithBroaderQuery?: () => void;
}

export function InsufficientEvidenceGuard({ onRetryWithBroaderQuery }: InsufficientEvidenceGuardProps) {
  return (
    <div className="my-6 rounded-xl border-2 border-dashed border-amber-300 bg-amber-50/70 p-6 text-center shadow-gst-subtle space-y-4">
      <div className="mx-auto h-12 w-12 rounded-full bg-amber-100 border border-amber-300 flex items-center justify-center text-amber-700 shadow-2xs">
        <ShieldOff className="h-6 w-6" />
      </div>

      <div className="space-y-1.5 max-w-lg mx-auto">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-200/80 text-amber-950 font-black text-xs uppercase tracking-wider">
          UNVERIFIED — INSUFFICIENT GST EVIDENCE
        </div>
        <h3 className="text-base font-extrabold text-amber-950 tracking-tight">
          No Grounded Legal Chunks Met Relevance Criteria
        </h3>
        <p className="text-xs text-amber-800/90 leading-relaxed font-medium">
          GST Sahayak enforce strict hallucination protection. Because zero relevant official documents met the similarity threshold, <strong>0 LLM calls were executed</strong>.
        </p>
      </div>

      <div className="pt-2">
        {onRetryWithBroaderQuery && (
          <Button
            size="sm"
            variant="outline"
            onClick={onRetryWithBroaderQuery}
            className="border-amber-400 bg-white text-amber-900 hover:bg-amber-100 font-bold text-xs gap-1.5"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Re-phrase Query with Broader Keywords
          </Button>
        )}
      </div>
    </div>
  );
}
