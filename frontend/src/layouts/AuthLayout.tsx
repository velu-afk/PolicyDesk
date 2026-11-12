import React from 'react';
import { ShieldCheck, Lock, FileSearch, Sparkles } from 'lucide-react';

export const AuthLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen grid lg:grid-cols-12 bg-slate-950">
      {/* Left Enterprise Branding Panel */}
      <div className="hidden lg:flex lg:col-span-6 flex-col justify-between p-12 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white border-r border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/30">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight block leading-none">
              PolicyDesk
            </span>
            <span className="text-xs text-indigo-300 font-medium tracking-wider uppercase">
              PolicyDesk • AI-Powered Policy Assistant
            </span>
          </div>
        </div>

        <div className="space-y-8 max-w-lg">
          <div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 mb-4">
              <Sparkles className="w-3.5 h-3.5" />
              Zero-Hallucination Enterprise RAG
            </span>
            <h1 className="text-3xl font-bold tracking-tight text-white leading-tight">
              Instant, verifiable answers grounded strictly in your organization’s policies.
            </h1>
            <p className="text-slate-300 text-sm mt-3 leading-relaxed">
              Upload corporate PDFs and policy documents, index them with Google Gemini semantic embeddings and PostgreSQL pgvector, and empower teams with source-cited conversational search.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4">
            <div className="flex items-start gap-3.5 p-4 rounded-xl bg-white/5 border border-white/10">
              <FileSearch className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Verbatim Source Attribution
                </h3>
                <p className="text-xs text-slate-300 mt-0.5">
                  Every answer displays exact retrieved passages, document names, page numbers, and cosine similarity scores.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3.5 p-4 rounded-xl bg-white/5 border border-white/10">
              <Lock className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Role-Based Access Control (RBAC)
                </h3>
                <p className="text-xs text-slate-300 mt-0.5">
                  Administrators curate and audit the document repository while authenticated users query approved policies safely.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="text-xs text-slate-400 flex items-center justify-between">
          <span>PolicyDesk v1.0 • FastAPI + React + Neon pgvector + Gemini</span>
          <span>Strict Grounding Mode</span>
        </div>
      </div>

      {/* Right Form Container */}
      <div className="col-span-12 lg:col-span-6 flex items-center justify-center p-6 sm:p-12 bg-slate-50">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
};
