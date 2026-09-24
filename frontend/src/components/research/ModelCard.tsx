import React from 'react';
import { ModelAnswerResult } from '../../types';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { CheckCircle2, XCircle, AlertTriangle, Clock, ArrowRight, Bot } from 'lucide-react';

interface ModelCardProps {
  providerName: 'gemini' | 'mistral' | 'grok' | 'ollama' | string;
  result?: ModelAnswerResult;
  loading: boolean;
  onViewResponse: (result: ModelAnswerResult) => void;
}

const PROVIDER_NAMES: Record<string, string> = {
  gemini: 'GEMINI',
  mistral: 'MISTRAL',
  grok: 'GROK',
  ollama: 'OLLAMA',
};

const DEFAULT_MODELS: Record<string, string> = {
  gemini: 'gemini-3.6-flash',
  mistral: 'mistral-large-latest',
  grok: 'grok-beta',
  ollama: 'qwen2.5:7b-instruct',
};

export function ModelCard({ providerName, result, loading, onViewResponse }: ModelCardProps) {
  const displayName = PROVIDER_NAMES[providerName.toLowerCase()] || providerName.toUpperCase();
  const defaultModel = DEFAULT_MODELS[providerName.toLowerCase()] || 'standard-model';

  if (loading) {
    return (
      <Card className="bg-white border-gst-border p-4 flex flex-col justify-between h-64 shadow-2xs">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-4 w-16 rounded-full" />
          </div>
          <Skeleton className="h-3 w-32" />
          <div className="space-y-2 pt-2">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
            <Skeleton className="h-3 w-4/6" />
          </div>
        </div>
        <div className="pt-4 border-t border-gst-border/30 flex items-center justify-between">
          <Skeleton className="h-4 w-12" />
          <Skeleton className="h-8 w-24 rounded-lg" />
        </div>
      </Card>
    );
  }

  // Provider states: SUCCESS, FAILED, UNCONFIGURED
  const isSuccess = result?.success === true;
  const isUnconfigured = result && !result.success && (
    result.error?.toLowerCase().includes('not configured') ||
    result.error?.toLowerCase().includes('api_key') ||
    result.error?.toLowerCase().includes('missing')
  );
  const isFailed = result && !result.success && !isUnconfigured;

  const modelIdentifier = result?.model || defaultModel;
  const responseTimeStr = result?.response_time ? `${result.response_time.toFixed(2)}s` : null;

  return (
    <Card className={`flex flex-col justify-between h-full bg-white border-gst-border/90 shadow-gst-subtle hover:shadow-gst-card transition-all duration-200 ${
      isSuccess ? 'border-l-4 border-l-gst-green' : isFailed ? 'border-l-4 border-l-gst-red' : 'border-l-4 border-l-amber-400'
    }`}>
      {/* Header */}
      <CardHeader className="p-4 pb-2 border-b border-gst-border/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`h-2.5 w-2.5 rounded-full ${
              isSuccess ? 'bg-gst-green shadow-xs shadow-gst-green' : isFailed ? 'bg-gst-red' : 'bg-amber-400'
            }`} />
            <CardTitle className="text-sm font-extrabold tracking-tight text-gst-dark">
              {displayName}
            </CardTitle>
          </div>

          {/* Status Badge */}
          {isSuccess && (
            <Badge variant="success" className="text-[10px] uppercase font-bold py-0.5 px-2">
              <CheckCircle2 className="h-3 w-3 mr-1" /> SUCCESS
            </Badge>
          )}
          {isFailed && (
            <Badge variant="destructive" className="text-[10px] uppercase font-bold py-0.5 px-2">
              <XCircle className="h-3 w-3 mr-1" /> FAILED
            </Badge>
          )}
          {isUnconfigured && (
            <Badge variant="warning" className="text-[10px] uppercase font-bold py-0.5 px-2">
              <AlertTriangle className="h-3 w-3 mr-1" /> UNCONFIGURED
            </Badge>
          )}
          {!result && (
            <Badge variant="outline" className="text-[10px] uppercase font-semibold py-0.5 px-2 text-gst-muted">
              STANDBY
            </Badge>
          )}
        </div>
        <div className="text-[11px] font-mono text-gst-muted truncate mt-0.5">
          {modelIdentifier}
        </div>
      </CardHeader>

      {/* Answer Preview Content */}
      <CardContent className="p-4 flex-1 text-xs text-gst-dark leading-relaxed">
        {isSuccess && result?.answer ? (
          <p className="line-clamp-5 font-sans text-gst-dark/90">
            {result.answer.replace(/[#*`_]/g, '')}
          </p>
        ) : isUnconfigured ? (
          <div className="bg-amber-50/70 border border-amber-200/60 rounded-lg p-3 text-amber-900 space-y-1">
            <div className="font-semibold flex items-center gap-1.5 text-xs">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-600" /> Key Not Configured
            </div>
            <p className="text-[11px] opacity-80 leading-snug">
              {result?.error || 'Provider API key is not set in backend environment.'}
            </p>
          </div>
        ) : isFailed ? (
          <div className="bg-gst-red/10 border border-gst-red/20 rounded-lg p-3 text-gst-red space-y-1">
            <div className="font-semibold flex items-center gap-1.5 text-xs">
              <XCircle className="h-3.5 w-3.5" /> Generation Error
            </div>
            <p className="text-[11px] opacity-90 line-clamp-4 leading-snug">
              {result?.error || 'Failed to complete LLM response.'}
            </p>
          </div>
        ) : (
          <div className="text-gst-muted text-center py-6 font-medium italic text-xs">
            Awaiting verification query...
          </div>
        )}
      </CardContent>

      {/* Card Footer */}
      <CardFooter className="p-4 pt-2 border-t border-gst-border/30 flex items-center justify-between mt-auto">
        <div className="text-[11px] text-gst-muted font-medium flex items-center gap-1">
          {responseTimeStr && (
            <>
              <Clock className="h-3 w-3 text-gst-orange-deep" />
              <span>{responseTimeStr}</span>
            </>
          )}
        </div>

        {isSuccess && result && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onViewResponse(result)}
            className="text-xs text-gst-orange-deep font-bold hover:bg-gst-orange-verylight hover:text-gst-dark px-2.5 h-8 gap-1"
          >
            View response <ArrowRight className="h-3 w-3" />
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
