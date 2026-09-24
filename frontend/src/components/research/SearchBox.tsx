import React, { useState } from 'react';
import { Search, Calendar, Filter, ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

interface SearchBoxProps {
  initialQuery?: string;
  initialFY?: string;
  initialAsOfDate?: string;
  placeholder?: string;
  buttonText?: string;
  loading: boolean;
  onSearch: (query: string, financialYear: string, asOfDate: string) => void;
  suggestedQuestions?: string[];
}

const DEFAULT_SUGGESTIONS = [
  "Section 16 conditions for ITC",
  "Input Tax Credit eligibility",
  "Reverse Charge Mechanism (RCM)",
  "ITC Reversal rules under GST",
];

export function SearchBox({
  initialQuery = '',
  initialFY = '',
  initialAsOfDate = '',
  placeholder = "Ask a GST question...",
  buttonText = "Search →",
  loading,
  onSearch,
  suggestedQuestions = DEFAULT_SUGGESTIONS,
}: SearchBoxProps) {
  const [query, setQuery] = useState(initialQuery);
  const [financialYear, setFinancialYear] = useState(initialFY);
  const [asOfDate, setAsOfDate] = useState(initialAsOfDate);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;
    onSearch(query.trim(), financialYear, asOfDate);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    if (!loading) {
      onSearch(suggestion, financialYear, asOfDate);
    }
  };

  return (
    <div className="w-full space-y-4">
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Main Search Input Box */}
        <div className="relative flex items-center rounded-xl border border-gst-border bg-white shadow-gst-card p-1.5 transition-all focus-within:ring-2 focus-within:ring-gst-orange focus-within:border-gst-orange">
          <div className="pl-3.5 pr-2 text-gst-muted">
            <Search className="h-5 w-5" />
          </div>
          <Input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            disabled={loading}
            className="border-0 shadow-none focus-visible:ring-0 text-base py-3 px-1 font-medium placeholder:font-normal placeholder:text-gst-muted/60"
          />
          <Button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-gst-orange hover:bg-gst-orange-hover text-gst-dark font-bold px-5 h-11 rounded-lg shrink-0 transition-transform active:scale-95"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin text-sm">⏳</span> Searching...
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                {buttonText}
              </span>
            )}
          </Button>
        </div>

        {/* Temporal Context Controls (Financial Year & As-of Date) */}
        <div className="flex flex-wrap items-center gap-3 px-1 py-1 text-xs text-gst-muted">
          <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-gst-border/60 shadow-2xs">
            <Filter className="h-3.5 w-3.5 text-gst-orange-deep" />
            <label className="font-semibold text-gst-dark">Financial Year:</label>
            <select
              value={financialYear}
              onChange={(e) => setFinancialYear(e.target.value)}
              disabled={loading}
              className="bg-transparent font-medium text-gst-dark focus:outline-none cursor-pointer"
            >
              <option value="">All Financial Years (Default)</option>
              <option value="2024-25">FY 2024-25</option>
              <option value="2025-26">FY 2025-26</option>
              <option value="2026-27">FY 2026-27</option>
            </select>
          </div>

          <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-gst-border/60 shadow-2xs">
            <Calendar className="h-3.5 w-3.5 text-gst-orange-deep" />
            <label className="font-semibold text-gst-dark">As-of Date:</label>
            <input
              type="date"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              disabled={loading}
              className="bg-transparent font-medium text-gst-dark focus:outline-none cursor-pointer"
            />
          </div>
        </div>
      </form>

      {/* Suggested Quick Questions */}
      {suggestedQuestions && suggestedQuestions.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-xs font-semibold text-gst-muted flex items-center gap-1">
            <Sparkles className="h-3 w-3 text-gst-orange-deep" /> Suggestions:
          </span>
          {suggestedQuestions.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => handleSuggestionClick(q)}
              disabled={loading}
              className="text-xs bg-white hover:bg-gst-orange-verylight text-gst-dark font-medium border border-gst-border/70 hover:border-gst-orange/50 px-2.5 py-1 rounded-full transition-all cursor-pointer shadow-2xs"
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
