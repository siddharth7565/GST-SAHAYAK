import React, { useState, useEffect } from 'react';
import { HistoryItem, SavedQueryItem } from '../types';
import { getHistory, getSavedQueries } from '../lib/storage';
import { SearchBox } from '../components/research/SearchBox';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { formatPercent, formatDate } from '../lib/utils';
import { Scale, Sparkles, ShieldCheck, History, Bookmark, ArrowRight, CheckCircle2, FileText, Activity } from 'lucide-react';

interface DashboardProps {
  onNavigate: (nav: 'single' | 'multi' | 'history' | 'saved', initialQuery?: string) => void;
  onRunSearch: (query: string, mode: 'single' | 'multi', fy: string, asOfDate: string) => void;
}

export function Dashboard({ onNavigate, onRunSearch }: DashboardProps) {
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [savedItems, setSavedItems] = useState<SavedQueryItem[]>([]);

  useEffect(() => {
    setHistoryItems(getHistory());
    setSavedItems(getSavedQueries());
  }, []);

  // Compute real statistics from history (No hardcoded/fake numbers)
  const totalQueries = historyItems.length;
  const verifiedAnswersCount = historyItems.filter(
    h => h.verificationLevel === 'HIGH' || h.verificationLevel === 'MEDIUM'
  ).length;

  const evidenceSourcesCount = historyItems.reduce((sum, item) => {
    if (item.ragResult) return sum + (item.ragResult.retrieved_count || 0);
    if (item.verifyResult) return sum + (item.verifyResult.retrieved_count || 0);
    return sum;
  }, 0);

  const avgScoreVal = totalQueries > 0
    ? historyItems.reduce((acc, h) => acc + (h.verificationScore || 0), 0) / totalQueries
    : null;

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Welcome / Research Heading Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-gst-orange-verylight via-white to-gst-cream border border-gst-border/80 p-6 md:p-8 shadow-gst-subtle relative overflow-hidden">
        <div className="max-w-2xl space-y-3 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gst-orange-light text-gst-orange-deep text-xs font-extrabold uppercase tracking-wider border border-gst-orange/30">
            <Scale className="h-3.5 w-3.5" /> GST Sahayak Legal Workbench
          </div>
          <h2 className="text-2xl md:text-3xl font-black text-gst-dark tracking-tight leading-snug">
            AI-Powered GST Legal Research & Verification System
          </h2>
          <p className="text-xs md:text-sm text-gst-muted leading-relaxed font-normal">
            Ground your GST legal research with official CBIC acts, rules, notifications, and cross-model answer verification tailored for tax practitioners and legal experts.
          </p>
        </div>
      </div>

      {/* Quick Research Launcher */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-extrabold uppercase tracking-wider text-gst-dark flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-gst-orange-deep" /> Quick Research Launcher
          </h3>
        </div>

        <Card className="p-6 bg-white border-gst-border shadow-gst-card">
          <SearchBox
            placeholder="Ask a GST legal question (e.g. Section 16 conditions, RCM rules)..."
            buttonText="Start Research"
            loading={false}
            onSearch={(query, fy, asOfDate) => {
              onRunSearch(query, 'single', fy, asOfDate);
            }}
          />

          <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-gst-border/40 mt-4">
            <span className="text-xs font-semibold text-gst-muted">Launch Mode:</span>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onNavigate('single')}
              className="gap-2 text-xs font-bold"
            >
              <Sparkles className="h-3.5 w-3.5" /> Single LLM Research
            </Button>
            <Button
              size="sm"
              onClick={() => onNavigate('multi')}
              className="bg-gst-orange hover:bg-gst-orange-hover text-gst-dark font-bold text-xs gap-2"
            >
              <ShieldCheck className="h-3.5 w-3.5" /> Multi LLM Verification
            </Button>
          </div>
        </Card>
      </div>

      {/* Compact Real Statistics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-white border-gst-border/80 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gst-muted uppercase">Total Queries</span>
            <div className="p-2 rounded-lg bg-gst-orange-verylight text-gst-orange-deep">
              <History className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-gst-dark mt-2 tracking-tight">
            {totalQueries}
          </div>
          <div className="text-[10px] text-gst-muted mt-1 font-medium">Recorded sessions</div>
        </Card>

        <Card className="p-4 bg-white border-gst-border/80 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gst-muted uppercase">Verified Answers</span>
            <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-gst-dark mt-2 tracking-tight">
            {verifiedAnswersCount}
          </div>
          <div className="text-[10px] text-gst-muted mt-1 font-medium">High / Medium signal</div>
        </Card>

        <Card className="p-4 bg-white border-gst-border/80 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gst-muted uppercase">Evidence Sources</span>
            <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
              <FileText className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-gst-dark mt-2 tracking-tight">
            {evidenceSourcesCount}
          </div>
          <div className="text-[10px] text-gst-muted mt-1 font-medium">Retrieved GST chunks</div>
        </Card>

        <Card className="p-4 bg-white border-gst-border/80 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gst-muted uppercase">Avg Verification</span>
            <div className="p-2 rounded-lg bg-purple-50 text-purple-600">
              <Activity className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-gst-dark mt-2 tracking-tight">
            {avgScoreVal !== null ? formatPercent(avgScoreVal) : 'N/A'}
          </div>
          <div className="text-[10px] text-gst-muted mt-1 font-medium">Overall average score</div>
        </Card>
      </div>

      {/* Recent Research List Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-extrabold uppercase tracking-wider text-gst-dark flex items-center gap-2">
            <History className="h-4 w-4 text-gst-orange-deep" /> Recent Research History
          </h3>
          <Button
            variant="link"
            onClick={() => onNavigate('history')}
            className="text-xs text-gst-orange-deep font-bold p-0"
          >
            View all history →
          </Button>
        </div>

        {historyItems.length === 0 ? (
          <Card className="p-8 text-center bg-white border-dashed border-gst-border">
            <div className="text-sm font-bold text-gst-dark mb-1">No research sessions recorded yet</div>
            <div className="text-xs text-gst-muted mb-4">
              Search a GST legal question above to generate grounded RAG answers and verification signals.
            </div>
          </Card>
        ) : (
          <div className="grid gap-3">
            {historyItems.slice(0, 5).map((item) => (
              <Card
                key={item.id}
                onClick={() => onNavigate(item.mode, item.query)}
                className="p-4 bg-white hover:border-gst-orange/60 transition-all cursor-pointer shadow-2xs hover:shadow-gst-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1 min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] font-bold uppercase py-0.5">
                      {item.mode === 'multi' ? 'Multi LLM' : 'Single LLM'}
                    </Badge>
                    <span className="text-xs font-bold text-gst-dark truncate">
                      {item.query}
                    </span>
                  </div>
                  <div className="text-[11px] text-gst-muted flex items-center gap-3">
                    <span>{formatDate(item.timestamp)}</span>
                    {item.financialYear && (
                      <span className="font-semibold text-gst-orange-deep">FY {item.financialYear}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {item.verificationLevel && (
                    <Badge
                      variant={
                        item.verificationLevel === 'HIGH'
                          ? 'success'
                          : item.verificationLevel === 'MEDIUM'
                          ? 'warning'
                          : 'destructive'
                      }
                      className="text-[10px] font-bold uppercase"
                    >
                      {item.verificationLevel} ({formatPercent(item.verificationScore)})
                    </Badge>
                  )}
                  <ArrowRight className="h-4 w-4 text-gst-muted" />
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
