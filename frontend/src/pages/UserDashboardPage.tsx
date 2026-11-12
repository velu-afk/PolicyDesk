import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  MessageSquareText,
  FileText,
  Sparkles,
  ArrowRight,
  History,
  Search,
} from 'lucide-react';
import { documentService } from '../services/documentService';
import { chatService } from '../services/chatService';
import { ConversationSummary, DocumentItem } from '../types';
import { useAuth } from '../hooks/useAuth';

const EXAMPLE_QUESTIONS = [
  'How many days per week are full-time employees required to work in the office?',
  'What is the home office setup stipend and monthly internet reimbursement limit?',
  'Within how many hours must a suspected security breach or lost device be reported?',
  'How many days of annual Paid Time Off (PTO) can be carried over into the next year?',
];

export const UserDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [quickQuestion, setQuickQuestion] = useState('');

  useEffect(() => {
    documentService.listProcessedDocuments().then(setDocuments).catch(console.error);
    chatService.listConversations().then(setConversations).catch(console.error);
  }, []);

  const handleQuickSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickQuestion.trim()) return;
    navigate(`/chat?q=${encodeURIComponent(quickQuestion.trim())}`);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Hero Banner with Direct Question Input */}
      <div className="rounded-3xl bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white p-8 shadow-lg">
        <div className="max-w-3xl">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            Verified Policy Knowledge Base
          </span>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Hello, {user?.name}. What policy question can I answer for you today?
          </h1>
          <p className="text-sm text-slate-300 mt-2">
            Ask any question about company guidelines, security protocols, or employee benefits. Every answer includes verifiable document citations and source passages.
          </p>

          <form onSubmit={handleQuickSubmit} className="mt-6 flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={quickQuestion}
                onChange={(e) => setQuickQuestion(e.target.value)}
                placeholder="Ask about hybrid work days, PTO carryover, travel reimbursement, or security SLAs..."
                className="w-full pl-11 pr-4 py-3 rounded-xl bg-white text-slate-900 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <button
              type="submit"
              className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold inline-flex items-center justify-center gap-2 transition-colors shrink-0"
            >
              <span>Ask PolicyDesk AI</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Suggested Starter Chips */}
          <div className="mt-5">
            <p className="text-xs font-semibold text-indigo-300 mb-2">
              Suggested policy questions:
            </p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => navigate(`/chat?q=${encodeURIComponent(q)}`)}
                  className="text-left text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-slate-100 border border-white/10 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Two-Column Overview: Available Documents & Recent Conversations */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Active Policy Documents ({documents.length})
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Approved documents currently indexed for semantic retrieval.
              </p>
            </div>
            <Link
              to="/chat"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 inline-flex items-center gap-1"
            >
              <span>Open Chat</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {documents.length === 0 ? (
            <div className="py-10 text-center text-xs text-slate-500">
              No processed policy documents are available yet.
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="p-4 rounded-xl border border-slate-200 hover:border-indigo-200 bg-slate-50/60 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText className="w-4 h-4 text-indigo-600 shrink-0" />
                      <h3 className="text-sm font-semibold text-slate-900 truncate">
                        {doc.filename}
                      </h3>
                    </div>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100 shrink-0">
                      {doc.chunk_count} chunks
                    </span>
                  </div>
                  {doc.summary && (
                    <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                      {doc.summary}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Your Recent Conversations
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Resume previous Q&A sessions with full source citations.
              </p>
            </div>
            <Link
              to="/history"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 inline-flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {conversations.length === 0 ? (
            <div className="py-10 text-center">
              <History className="w-8 h-8 text-slate-400 mx-auto mb-2" />
              <p className="text-xs text-slate-500">
                You haven’t started any conversations yet.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {conversations.slice(0, 6).map((conv) => (
                <Link
                  key={conv.id}
                  to={`/chat?conversationId=${conv.id}`}
                  className="block p-3.5 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-slate-900 truncate">
                      {conv.title}
                    </span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 shrink-0">
                      {conv.message_count} msgs
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">
                    {new Date(conv.created_at).toLocaleString()}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
