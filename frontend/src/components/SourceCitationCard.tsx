import React, { useState } from 'react';
import { FileText, ChevronDown, ChevronUp, BookOpen } from 'lucide-react';
import { SourceAttribution } from '../types';

interface SourceCitationCardProps {
  source: SourceAttribution;
  index: number;
}

export const SourceCitationCard: React.FC<SourceCitationCardProps> = ({
  source,
  index,
}) => {
  const [expanded, setExpanded] = useState<boolean>(index === 0);
  const matchPercent = Math.round(source.similarity_score * 100);

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/90 overflow-hidden transition-all">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full px-3.5 py-2.5 flex items-center justify-between text-left hover:bg-slate-100/80 transition-colors"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-md bg-indigo-600 text-white text-[11px] font-bold shrink-0">
            {index + 1}
          </span>
          <FileText className="w-4 h-4 text-indigo-600 shrink-0" />
          <span className="text-xs font-semibold text-slate-900 truncate">
            {source.source_document_name}
          </span>
          {source.page_number && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-white border border-slate-200 text-slate-700 shrink-0">
              Page {source.page_number}
            </span>
          )}
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-100 shrink-0">
            Chunk #{source.chunk_index}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0 ml-2">
          <span
            className="text-[11px] font-mono font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded"
            title="Cosine similarity score"
          >
            {matchPercent}% match
          </span>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-slate-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-500" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 py-3 bg-white border-t border-slate-200/80">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 mb-1.5">
            <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
            <span>Retrieved Verbatim Passage (Doc ID #{source.source_document_id}):</span>
          </div>
          <blockquote className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-lg border-l-4 border-indigo-500 font-mono whitespace-pre-wrap">
            {source.relevant_passage}
          </blockquote>
        </div>
      )}
    </div>
  );
};
