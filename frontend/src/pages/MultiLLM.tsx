import React, { useState } from 'react';
import { MultiModelResponse, ModelAnswerResult, PipelineStage } from '../types';
import { sendMultiModelVerification } from '../api';
import { saveHistoryItem, toggleSaveQuery, isQuerySaved } from '../lib/storage';
import { SearchBox } from '../components/research/SearchBox';
import { PipelineStepper } from '../components/research/PipelineStepper';
import { ModelCard } from '../components/research/ModelCard';
import { ModelResponseDialog } from '../components/research/ModelResponseDialog';
import { VerificationResult } from '../components/research/VerificationResult';
import { EvidenceSection } from '../components/research/EvidenceCard';
import { InsufficientEvidenceGuard } from '../components/research/InsufficientEvidenceGuard';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Alert, AlertTitle, AlertDescription } from '../components/ui/alert';
import { ShieldCheck, Bookmark, BookmarkCheck, AlertTriangle, Layers, Cpu } from 'lucide-react';

interface MultiLLMProps {
  initialQuery?: string;
  initialFY?: string;
  initialAsOfDate?: string;
}

const PROVIDER_LIST = ['gemini', 'mistral', 'grok', 'ollama'];

export function MultiLLM({ initialQuery = '', initialFY = '', initialAsOfDate = '' }: MultiLLMProps) {
  const [loading, setLoading] = useState(false);
  const [pipelineStage, setPipelineStage] = useState<PipelineStage>('IDLE');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MultiModelResponse | null>(null);
  const [currentQuery, setCurrentQuery] = useState(initialQuery);
  const [appliedFY, setAppliedFY] = useState(initialFY);
  const [appliedAsOfDate, setAppliedAsOfDate] = useState(initialAsOfDate);
  const [saved, setSaved] = useState(false);

  // Dialog state for selected model answer modal
  const [selectedModelResult, setSelectedModelResult] = useState<ModelAnswerResult | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleSearch = async (query: string, fy: string, asOfDate: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentQuery(query);
    setAppliedFY(fy);
    setAppliedAsOfDate(asOfDate);
    setSaved(isQuerySaved(query));

    // Progressive pipeline stepper states
    setPipelineStage('RETRIEVING');

    try {
      // Simulate realistic step transitions
      setTimeout(() => setPipelineStage('GENERATING'), 600);
      setTimeout(() => setPipelineStage('COMPARING'), 1800);
      setTimeout(() => setPipelineStage('VERIFYING'), 2500);

      const data = await sendMultiModelVerification(
        query,
        5,
        fy || null,
        asOfDate || null,
        ['gemini', 'mistral', 'grok', 'ollama']
      );

      setResult(data);
      setPipelineStage('COMPLETE');

      // Persist to history
      saveHistoryItem({
        query,
        mode: 'multi',
        financialYear: fy,
        asOfDate,
        verificationLevel: data.verification?.verification_level,
        verificationScore: data.verification?.verification_score,
        verifyResult: data,
      });
    } catch (err: any) {
      setError(err.message || 'Multi-model verification failed. Please try again.');
      setPipelineStage('IDLE');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSave = () => {
    if (!currentQuery) return;
    const res = toggleSaveQuery(currentQuery, 'multi', appliedFY, appliedAsOfDate);
    setSaved(res.saved);
  };

  const handleViewResponse = (modelRes: ModelAnswerResult) => {
    setSelectedModelResult(modelRes);
    setDialogOpen(true);
  };

  // Map returned model_results array by provider key for quick lookup
  const modelResultMap: Record<string, ModelAnswerResult> = {};
  if (result && result.model_results) {
    result.model_results.forEach(res => {
      modelResultMap[res.provider.toLowerCase()] = res;
    });
  }

  const isInsufficientState = result && result.evidence_status === 'insufficient' && result.model_results.length === 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="border-b border-gst-border pb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-gst-orange-light text-gst-orange-deep font-bold">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-gst-dark tracking-tight">MULTI LLM VERIFICATION</h2>
            <p className="text-xs text-gst-muted">
              Compare multiple AI models against identical GST evidence to eliminate hallucination.
            </p>
          </div>
        </div>
      </div>

      {/* Main Search Box */}
      <SearchBox
        initialQuery={initialQuery}
        initialFY={initialFY}
        initialAsOfDate={initialAsOfDate}
        placeholder="Ask a GST question for verification across Gemini, Mistral, Grok & Ollama..."
        buttonText="Verify Answers"
        loading={loading}
        onSearch={handleSearch}
      />

      {/* Workflow Stepper */}
      <PipelineStepper stage={pipelineStage} />

      {/* Error State */}
      {error && (
        <Alert variant="destructive" className="my-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle className="font-bold text-xs">Verification Error</AlertTitle>
          <AlertDescription className="text-xs">
            {error}
          </AlertDescription>
        </Alert>
      )}

      {/* Query Bar & Action Controls */}
      {result && (
        <Card className="bg-white border-gst-border p-4 shadow-2xs">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-[10px] font-extrabold uppercase tracking-wider text-gst-muted">
                Active Verification Query
              </div>
              <h3 className="text-sm font-bold text-gst-dark mt-0.5">
                Q: {result.query}
              </h3>
              {(appliedFY || appliedAsOfDate) && (
                <div className="flex items-center gap-2 text-xs text-gst-orange-deep mt-1 font-semibold">
                  <span>🗓️ Applied Filters:</span>
                  {appliedFY && <span>FY: {appliedFY}</span>}
                  {appliedAsOfDate && <span>As-of: {appliedAsOfDate}</span>}
                </div>
              )}
            </div>

            <Button
              size="sm"
              variant="outline"
              onClick={handleToggleSave}
              className="gap-1.5 text-xs font-bold border-gst-border"
            >
              {saved ? (
                <>
                  <BookmarkCheck className="h-4 w-4 text-gst-orange-deep" /> Saved
                </>
              ) : (
                <>
                  <Bookmark className="h-4 w-4" /> Save Query
                </>
              )}
            </Button>
          </div>
        </Card>
      )}

      {/* Verification Result Signal Banner */}
      {result?.verification && (
        <VerificationResult
          verification={result.verification}
          comparison={result.comparison}
        />
      )}

      {/* Insufficient Evidence State Guard */}
      {isInsufficientState ? (
        <InsufficientEvidenceGuard
          onRetryWithBroaderQuery={() => {
            const searchInput = document.querySelector('input[type="text"]') as HTMLInputElement;
            if (searchInput) searchInput.focus();
          }}
        />
      ) : (
        <>
          {/* SECTION 13 & 14: FOUR MODEL PROVIDERS IN ONE SECTION */}
          <div className="space-y-3 my-6">
            <div className="flex items-center justify-between border-b border-gst-border pb-2">
              <div className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-gst-orange-deep" />
                <h3 className="text-sm font-extrabold uppercase tracking-wider text-gst-dark">
                  MULTI-LLM ANSWERS POOL
                </h3>
              </div>
              <Badge variant="outline" className="text-xs text-gst-muted font-mono">
                4 Providers Grid
              </Badge>
            </div>

            {/* Responsive Grid: Desktop 4 cards, Tablet 2 cards, Mobile 1 card */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {PROVIDER_LIST.map((provider) => {
                const res = modelResultMap[provider];
                return (
                  <ModelCard
                    key={provider}
                    providerName={provider}
                    result={res}
                    loading={loading}
                    onViewResponse={handleViewResponse}
                  />
                );
              })}
            </div>
          </div>

          {/* Shared Evidence Section */}
          {result && (
            <EvidenceSection
              chunks={result.retrieved_chunks}
              retrievedCount={result.retrieved_count}
            />
          )}
        </>
      )}

      {/* Detailed Response Modal */}
      <ModelResponseDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        result={selectedModelResult}
      />
    </div>
  );
}
