import React, { useState } from 'react';
import { RetrievedChunk } from '../../types';
import { formatPercent } from '../../lib/utils';
import { FileText, ExternalLink, ChevronDown, ChevronUp, Layers, Award, Calendar, Bookmark } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';

interface EvidenceCardProps {
  chunks: RetrievedChunk[];
  retrievedCount: number;
}

export function EvidenceSection({ chunks, retrievedCount }: EvidenceCardProps) {
  const [expandedMap, setExpandedMap] = useState<Record<string, boolean>>({});

  const toggleExpand = (chunkId: string) => {
    setExpandedMap(prev => ({
      ...prev,
      [chunkId]: !prev[chunkId],
    }));
  };

  return (
    <div className="space-y-4 my-6">
      {/* Header Banner emphasizing Shared Evidence */}
      <div className="flex items-center justify-between border-b border-gst-border pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-gst-orange-light text-gst-orange-deep">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-extrabold text-gst-dark tracking-tight flex items-center gap-2">
              Retrieved GST Evidence Sources
              <Badge variant="default" className="text-xs bg-gst-orange/30 text-gst-orange-deep font-bold">
                {retrievedCount} Chunks
              </Badge>
            </h3>
            <p className="text-xs text-gst-muted">
              Identical pgvector grounded evidence passed into model prompts
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 text-xs text-gst-orange-deep font-semibold bg-gst-orange-verylight px-3 py-1 rounded-full border border-gst-orange/30">
          <Layers className="h-3.5 w-3.5" />
          <span>Shared Single-Retrieval Guarantee</span>
        </div>
      </div>

      {/* Zero Chunks State */}
      {retrievedCount === 0 || chunks.length === 0 ? (
        <Card className="bg-gst-cream/40 border-dashed border-gst-border p-6 text-center">
          <div className="text-sm font-semibold text-gst-dark mb-1">
            No matching GST legal documents met the similarity criteria.
          </div>
          <div className="text-xs text-gst-muted">
            Zero LLM calls were executed to preserve safety and prevent ungrounded hallucination.
          </div>
        </Card>
      ) : (
        <div className="grid gap-3">
          {chunks.map((chunk, idx) => {
            const isExpanded = !!expandedMap[chunk.chunk_id];
            const matchPercent = formatPercent(chunk.similarity_score);

            return (
              <Card
                key={chunk.chunk_id || idx}
                className="bg-white border-gst-border/80 hover:border-gst-orange/50 transition-all shadow-2xs hover:shadow-gst-subtle"
              >
                <div className="p-4 space-y-2.5">
                  {/* Card Header Row */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="h-6 w-6 rounded-md bg-gst-orange-light text-gst-orange-deep font-extrabold text-xs flex items-center justify-center shrink-0">
                        [{idx + 1}]
                      </span>
                      <h4 className="text-sm font-bold text-gst-dark truncate">
                        {chunk.title || chunk.document}
                      </h4>
                    </div>

                    <div className="flex items-center gap-2">
                      <Badge variant="default" className="bg-gst-orange-light text-gst-orange-deep font-bold text-xs">
                        <Award className="h-3 w-3 mr-1" />
                        {matchPercent} Match
                      </Badge>
                    </div>
                  </div>

                  {/* Metadata Tag Row */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    {chunk.retrieval_method && (
                      <span className="px-2 py-0.5 rounded bg-gst-subtle border border-gst-border text-gst-dark font-medium">
                        {chunk.retrieval_method === 'hybrid' && '⚡ Hybrid Match'}
                        {chunk.retrieval_method === 'vector_only' && '🧠 Vector Match'}
                        {chunk.retrieval_method === 'keyword_only' && '🔤 Keyword Match'}
                      </span>
                    )}

                    {chunk.document_type && (
                      <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200 font-semibold uppercase">
                        {chunk.document_type}
                      </span>
                    )}

                    <span className="px-2 py-0.5 rounded bg-gst-orange-verylight text-gst-dark border border-gst-border">
                      Page {chunk.page}
                    </span>

                    {chunk.financial_year && (
                      <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 font-medium">
                        FY {chunk.financial_year}
                      </span>
                    )}

                    {(chunk.effective_from || chunk.effective_to) && (
                      <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-medium flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        Eff: {chunk.effective_from || 'Start'} {chunk.effective_to ? `to ${chunk.effective_to}` : 'Onwards'}
                      </span>
                    )}

                    {chunk.issuing_authority && (
                      <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200 font-medium">
                        {chunk.issuing_authority}
                      </span>
                    )}
                  </div>

                  {/* Official Link if available */}
                  {chunk.source_url && (
                    <div>
                      <a
                        href={chunk.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-gst-orange-deep font-semibold hover:underline inline-flex items-center gap-1"
                      >
                        Official Source Document <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  )}

                  {/* Chunk Text Content Box */}
                  <div className="bg-gst-subtle/70 rounded-lg p-3 border border-gst-border/50 text-xs leading-relaxed text-gst-dark font-sans">
                    <p>
                      {isExpanded
                        ? chunk.text
                        : chunk.text.length > 200
                        ? `${chunk.text.slice(0, 200)}...`
                        : chunk.text}
                    </p>
                    {chunk.text.length > 200 && (
                      <button
                        type="button"
                        onClick={() => toggleExpand(chunk.chunk_id)}
                        className="mt-2 text-gst-orange-deep font-bold hover:underline inline-flex items-center gap-1 cursor-pointer text-xs"
                      >
                        {isExpanded ? (
                          <>Show Less <ChevronUp className="h-3 w-3" /></>
                        ) : (
                          <>Show Full Excerpt <ChevronDown className="h-3 w-3" /></>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
