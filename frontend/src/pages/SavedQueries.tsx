import React, { useState, useEffect } from 'react';
import { SavedQueryItem } from '../types';
import { getSavedQueries, deleteSavedQuery } from '../lib/storage';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { formatShortDate } from '../lib/utils';
import { Bookmark, Trash2, ArrowRight, Sparkles, ShieldCheck } from 'lucide-react';

interface SavedQueriesPageProps {
  onOpenQuery: (query: string, mode: 'single' | 'multi', fy?: string, asOfDate?: string) => void;
}

export function SavedQueriesPage({ onOpenQuery }: SavedQueriesPageProps) {
  const [savedItems, setSavedItems] = useState<SavedQueryItem[]>([]);

  useEffect(() => {
    setSavedItems(getSavedQueries());
  }, []);

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const updated = deleteSavedQuery(id);
    setSavedItems(updated);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="border-b border-gst-border pb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-gst-orange-light text-gst-orange-deep font-bold">
            <Bookmark className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-gst-dark tracking-tight">SAVED QUERIES</h2>
            <p className="text-xs text-gst-muted">Bookmarked GST questions for quick legal research access.</p>
          </div>
        </div>
      </div>

      {/* Saved Queries List */}
      {savedItems.length === 0 ? (
        <Card className="p-12 text-center bg-white border-dashed border-gst-border space-y-2">
          <Bookmark className="h-8 w-8 text-gst-muted mx-auto" />
          <div className="text-sm font-bold text-gst-dark">No saved queries yet</div>
          <div className="text-xs text-gst-muted max-w-sm mx-auto">
            Start saving important GST research for quick access by clicking "Save Query" during research.
          </div>
        </Card>
      ) : (
        <div className="grid gap-3">
          {savedItems.map((item) => (
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
                  <span>Saved on {formatShortDate(item.savedAt)}</span>
                  {item.financialYear && (
                    <span className="font-semibold text-gst-orange-deep">FY {item.financialYear}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <button
                  type="button"
                  onClick={(e) => handleDelete(e, item.id)}
                  className="p-1.5 text-gst-muted hover:text-gst-red hover:bg-gst-red/10 rounded-md transition-colors"
                  title="Remove bookmark"
                >
                  <Trash2 className="h-4 w-4" />
                </button>

                <Button
                  size="sm"
                  className="bg-gst-orange hover:bg-gst-orange-hover text-gst-dark font-bold text-xs gap-1"
                >
                  Run Query <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
