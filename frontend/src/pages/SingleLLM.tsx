import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { RAGResponse } from '../types';
import { sendRAGQuery } from '../api';
import { saveHistoryItem, toggleSaveQuery, isQuerySaved } from '../lib/storage';
import { SearchBox } from '../components/research/SearchBox';
import { EvidenceSection } from '../components/research/EvidenceCard';
import { VerificationResult } from '../components/research/VerificationResult';
import { InsufficientEvidenceGuard } from '../components/research/InsufficientEvidenceGuard';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Alert, AlertTitle, AlertDescription } from '../components/ui/alert';
import { Skeleton } from '../components/ui/skeleton';
import { Sparkles, Bookmark, BookmarkCheck, Share2, Bot, Clock, AlertTriangle, ShieldCheck } from 'lucide-react';

interface SingleLLMProps {
  initialQuery?: string;
  initialFY?: string;
  initialAsOfDate?: string;
}

export function SingleLLM({ initialQuery = '', initialFY = '', initialAsOfDate = '' }: SingleLLMProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RAGResponse | null>(null);
  const [currentQuery, setCurrentQuery] = useState(initialQuery);
  const [appliedFY, setAppliedFY] = useState(initialFY);
  const [appliedAsOfDate, setAppliedAsOfDate] = useState(initialAsOfDate);
  const [saved, setSaved] = useState(false);

  const handleSearch = async (query: string, fy: string, asOfDate: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentQuery(query);
    setAppliedFY(fy);
    setAppliedAsOfDate(asOfDate);
    setSaved(isQuerySaved(query));

    try {
      const data = await sendRAGQuery(query, 5, fy || null, asOfDate || null);
      setResult(data);

      // Save session to history
      saveHistoryItem({
        query,
        mode: 'single',
        financialYear: fy,
        asOfDate,
        verificationLevel: data.verification?.verification_level,
        verificationScore: data.verification?.verification_score,
        ragResult: data,
      });
    } catch (err: any) {
      setError(err.message || 'Unable to complete research query. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSave = () => {
    if (!currentQuery) return;
    const res = toggleSaveQuery(currentQuery, 'single', appliedFY, appliedAsOfDate);
    setSaved(res.saved);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="border-b border-gst-border pb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-gst-orange-light text-gst-orange-deep font-bold">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-gst-dark tracking-tight">SINGLE LLM</h2>
            <p className="text-xs text-gst-muted">Direct GST research using the configured AI model.</p>
          </div>
        </div>
      </div>

      {/* Main Search Area */}
      <SearchBox
        initialQuery={initialQuery}
        initialFY={initialFY}
        initialAsOfDate={initialAsOfDate}
        placeholder="Ask a GST question..."
        buttonText="Search →"
        loading={loading}
        onSearch={handleSearch}
      />

      {/* Error Message Display */}
      {error && (
        <Alert variant="destructive" className="my-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle className="font-bold text-xs">Research Request Error</AlertTitle>
          <AlertDescription className="text-xs">
            {error}
          </AlertDescription>
        </Alert>
      )}

      {/* Loading Shimmer State */}
      {loading && (
        <div className="space-y-4 my-6">
          <Card className="p-6 bg-white border-gst-border space-y-4">
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-4 rounded-full" />
              <Skeleton className="h-4 w-48" />
            </div>
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-10 w-full" />
          </Card>
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div className="space-y-6 animate-in slide-in-from-bottom-2 duration-300">
          {/* Query Summary & Action Bar */}
          <Card className="bg-white border-gst-border p-6 shadow-gst-card">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gst-border/50 pb-4">
              <div>
                <div className="text-[10px] font-extrabold uppercase tracking-wider text-gst-muted">
                  Queried Legal Topic
                </div>
                <h3 className="text-base font-bold text-gst-dark mt-0.5">
                  Q: {result.query}
                </h3>
                {(appliedFY || appliedAsOfDate) && (
                  <div className="flex items-center gap-2 text-xs text-gst-orange-deep mt-1 font-semibold">
                    <span>🗓️ Temporal Filters:</span>
                    {appliedFY && <span>FY: {appliedFY}</span>}
                    {appliedAsOfDate && <span>As-of: {appliedAsOfDate}</span>}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
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
            </div>

            {/* Deterministic Verification Signal */}
            {result.verification && (
              <VerificationResult verification={result.verification} />
            )}

            {/* Answer Box */}
            <div className="mt-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs font-extrabold uppercase tracking-wider text-gst-dark flex items-center gap-2">
                  <Bot className="h-4 w-4 text-gst-orange-deep" />
                  Grounded GST Legal Answer
                </div>
                <Badge variant="outline" className="text-[11px] font-mono text-gst-muted">
                  Gemini 3.6 Flash
                </Badge>
              </div>

              <div className="bg-gst-subtle/40 rounded-xl p-5 border border-gst-border/60 prose-gst">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {result.answer}
                </ReactMarkdown>
              </div>
            </div>
          </Card>

          {/* Evidence Section */}
          {result.evidence_status === 'insufficient' && result.retrieved_count === 0 ? (
            <InsufficientEvidenceGuard
              onRetryWithBroaderQuery={() => {
                const searchInput = document.querySelector('input[type="text"]') as HTMLInputElement;
                if (searchInput) searchInput.focus();
              }}
            />
          ) : (
            <EvidenceSection
              chunks={result.retrieved_chunks}
              retrievedCount={result.retrieved_count}
            />
          )}
        </div>
      )}
    </div>
  );
}
