import React, { useState, useEffect } from 'react';
import { HistoryItem } from '../types';
import { getHistory, clearHistory, deleteHistoryItem } from '../lib/storage';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { formatPercent, formatDate } from '../lib/utils';
import { History as HistoryIcon, Trash2, ArrowRight, Search, Scale, Sparkles, ShieldCheck } from 'lucide-react';
import { Input } from '../components/ui/input';

interface HistoryPageProps {
  onOpenQuery: (query: string, mode: 'single' | 'multi', fy?: string, asOfDate?: string) => void;
}

export function HistoryPage({ onOpenQuery }: HistoryPageProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [filterText, setFilterText] = useState('');

  useEffect(() => {
    setHistory(getHistory());
  }, []);

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear all query history?')) {
      clearHistory();
      setHistory([]);
    }
  };

  const handleDeleteItem = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const updated = deleteHistoryItem(id);
    setHistory(updated);
  };

  const filteredHistory = history.filter(item =>
    item.query.toLowerCase().includes(filterText.toLowerCase().trim())
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="border-b border-gst-border pb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-gst-orange-light text-gst-orange-deep font-bold">
            <HistoryIcon className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-gst-dark tracking-tight">QUERY HISTORY</h2>
            <p className="text-xs text-gst-muted">Audit log of past legal research sessions.</p>
          </div>
        </div>

        {history.length > 0 && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleClearAll}
            className="text-xs text-gst-red hover:bg-gst-red/10 border-gst-red/30 gap-1.5"
          >
            <Trash2 className="h-3.5 w-3.5" /> Clear History
          </Button>
        )}
      </div>

      {/* Filter Bar */}
      {history.length > 0 && (
        <div className="relative max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-3 text-gst-muted" />
          <Input
            type="text"
            placeholder="Search past queries..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="pl-9 text-xs"
          />
        </div>
      )}

      {/* History List */}
      {filteredHistory.length === 0 ? (
        <Card className="p-12 text-center bg-white border-dashed border-gst-border space-y-2">
          <HistoryIcon className="h-8 w-8 text-gst-muted mx-auto" />
          <div className="text-sm font-bold text-gst-dark">
            {filterText ? 'No matching history items found' : 'No query history recorded yet'}
          </div>
          <div className="text-xs text-gst-muted">
            {filterText ? 'Try adjusting your search filter' : 'Your completed GST legal queries will be automatically saved here.'}
          </div>
        </Card>
      ) : (
        <div className="grid gap-3">
          {filteredHistory.map((item) => (
            <Card
              key={item.id}
              onClick={() => onOpenQuery(item.query, item.mode, item.financialYear || '', item.asOfDate || '')}
              className="p-4 bg-white hover:border-gst-orange/70 transition-all cursor-pointer shadow-2xs hover:shadow-gst-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
            >
              <div className="space-y-1.5 min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <Badge
                    variant={item.mode === 'multi' ? 'default' : 'secondary'}
                    className="text-[10px] font-bold uppercase py-0.5"
                  >
                    {item.mode === 'multi' ? (
                      <span className="flex items-center gap-1"><ShieldCheck className="h-3 w-3" /> Multi LLM</span>
                    ) : (
                      <span className="flex items-center gap-1"><Sparkles className="h-3 w-3" /> Single LLM</span>
                    )}
                  </Badge>

                  <h3 className="text-sm font-bold text-gst-dark group-hover:text-gst-orange-deep transition-colors truncate">
                    {item.query}
                  </h3>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-[11px] text-gst-muted">
                  <span>🗓️ {formatDate(item.timestamp)}</span>
                  {item.financialYear && (
                    <span className="font-semibold text-gst-orange-deep">FY {item.financialYear}</span>
                  )}
                  {item.asOfDate && (
                    <span>As-of {item.asOfDate}</span>
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

                <button
                  type="button"
                  onClick={(e) => handleDeleteItem(e, item.id)}
                  className="p-1.5 text-gst-muted hover:text-gst-red hover:bg-gst-red/10 rounded-md transition-colors opacity-0 group-hover:opacity-100"
                  title="Delete from history"
                >
                  <Trash2 className="h-4 w-4" />
                </button>

                <ArrowRight className="h-4 w-4 text-gst-muted group-hover:text-gst-orange-deep transition-colors" />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
