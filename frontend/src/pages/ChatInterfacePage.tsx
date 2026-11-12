import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Send,
  PlusCircle,
  Sparkles,
  Bot,
  User as UserIcon,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  AlertTriangle,
  FileCheck2,
  MessageSquare,
} from 'lucide-react';
import { useChat } from '../hooks/useChat';
import { documentService } from '../services/documentService';
import { DocumentItem } from '../types';
import { SourceCitationCard } from '../components/SourceCitationCard';
import { useToast } from '../contexts/ToastContext';

const SUGGESTED_QUESTIONS = [
  'How many days per week must employees work from the office under the hybrid policy?',
  'What is the maximum home office stipend and monthly internet reimbursement?',
  'How quickly must an employee report a suspected security breach or lost laptop?',
  'How many weeks of paid parental leave are full-time employees eligible for?',
  'What are the nightly hotel and daily meal reimbursement limits for business travel?',
  'What is the company cryptocurrency trading matching bonus?', // Unrelated question to demonstrate honest fallback!
];

export const ChatInterfacePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [input, setInput] = useState('');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const initialQueryHandled = useRef(false);
  const { showToast } = useToast();

  const {
    conversations,
    activeConversationId,
    messages,
    lastRetrievalMeta,
    isSending,
    isLoadingHistory,
    error,
    fetchConversations,
    selectConversation,
    startNewConversation,
    sendQuestion,
    rateMessage,
  } = useChat();

  useEffect(() => {
    fetchConversations();
    documentService.listProcessedDocuments().then(setDocuments).catch(console.error);
  }, [fetchConversations]);

  useEffect(() => {
    const convIdParam = searchParams.get('conversationId');
    const queryParam = searchParams.get('q');

    if (convIdParam) {
      selectConversation(Number(convIdParam));
    } else if (queryParam && !initialQueryHandled.current) {
      initialQueryHandled.current = true;
      setSearchParams({}, { replace: true });
      sendQuestion(queryParam).catch(() => {});
    }
  }, [searchParams, selectConversation, sendQuestion, setSearchParams]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;
    const q = input.trim();
    setInput('');
    try {
      await sendQuestion(q, selectedDocIds);
    } catch {
      // Error is displayed inline by useChat
    }
  };

  const handleFeedback = async (
    messageId: number,
    feedback: 'helpful' | 'not_helpful'
  ) => {
    try {
      await rateMessage(messageId, feedback);
      showToast('info', 'Feedback Recorded', 'Thank you for rating this response.');
    } catch (err) {
      showToast(
        'error',
        'Could not save feedback',
        err instanceof Error ? err.message : undefined
      );
    }
  };

  const toggleDocFilter = (docId: number) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  return (
    <div className="max-w-7xl mx-auto h-[calc(100vh-8rem)] flex gap-6">
      {/* Left Conversation Switcher Panel */}
      <div className="hidden md:flex w-72 bg-white rounded-2xl border border-slate-200 flex-col overflow-hidden shrink-0 shadow-sm">
        <div className="p-4 border-b border-slate-200">
          <button
            onClick={() => {
              startNewConversation();
              setSearchParams({});
            }}
            className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-sm transition-colors"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New Conversation</span>
          </button>
        </div>

        {/* Optional Document Scope Filter */}
        {documents.length > 0 && (
          <div className="p-3.5 border-b border-slate-200 bg-slate-50/70">
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
              Filter Knowledge Scope ({selectedDocIds.length || 'All'})
            </p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {documents.map((doc) => {
                const active = selectedDocIds.includes(doc.id);
                return (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => toggleDocFilter(doc.id)}
                    className={`w-full text-left px-2.5 py-1.5 rounded-lg text-[11px] font-medium flex items-center gap-2 transition-colors ${
                      active
                        ? 'bg-indigo-100 text-indigo-900 font-semibold'
                        : 'text-slate-600 hover:bg-slate-200/60'
                    }`}
                  >
                    <FileCheck2
                      className={`w-3.5 h-3.5 shrink-0 ${
                        active ? 'text-indigo-600' : 'text-slate-400'
                      }`}
                    />
                    <span className="truncate">{doc.filename}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Recent Threads List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          <p className="px-2 text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
            Recent Threads
          </p>
          {conversations.length === 0 ? (
            <p className="text-xs text-slate-400 px-2 py-4">
              No saved threads yet. Ask a question to begin.
            </p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => selectConversation(conv.id)}
                className={`w-full text-left px-3 py-2.5 rounded-xl text-xs transition-all flex items-start gap-2.5 ${
                  activeConversationId === conv.id
                    ? 'bg-indigo-50 text-indigo-900 font-semibold border border-indigo-200'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5 mt-0.5 shrink-0 text-indigo-600" />
                <div className="min-w-0 flex-1">
                  <p className="truncate">{conv.title}</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    {conv.message_count} messages
                  </p>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Conversational RAG Area */}
      <div className="flex-1 bg-white rounded-2xl border border-slate-200 flex flex-col overflow-hidden shadow-sm">
        {/* Top Status Header */}
        <div className="px-6 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                PolicyDesk RAG Assistant
              </h2>
              <p className="text-[11px] text-slate-500">
                Answers strictly grounded in {documents.length} processed policy document(s)
              </p>
            </div>
          </div>

          {lastRetrievalMeta && (
            <div className="hidden sm:flex items-center gap-2 text-[11px] font-mono bg-white px-3 py-1 rounded-lg border border-slate-200 text-slate-600">
              <span>
                Retrieved: {lastRetrievalMeta.chunks_above_threshold}/
                {lastRetrievalMeta.chunks_evaluated} chunks
              </span>
              {lastRetrievalMeta.top_similarity_score != null && (
                <span className="text-indigo-600 font-semibold">
                  • Top Cosine: {(lastRetrievalMeta.top_similarity_score * 100).toFixed(0)}%
                </span>
              )}
            </div>
          )}
        </div>

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoadingHistory ? (
            <div className="h-full flex items-center justify-center text-sm text-slate-500 gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
              <span>Loading conversation history...</span>
            </div>
          ) : messages.length === 0 ? (
            <div className="max-w-2xl mx-auto py-8 text-center space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center mx-auto">
                <Sparkles className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Ask anything about your uploaded policies
                </h3>
                <p className="text-xs text-slate-500 mt-1 max-w-lg mx-auto leading-relaxed">
                  PolicyDesk embeds your question with Gemini, retrieves matching document chunks via pgvector cosine similarity, and cites exact source passages. If an answer is not in the uploaded documents, it will explicitly let you know.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => sendQuestion(q, selectedDocIds)}
                    className="p-3.5 rounded-xl border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 text-xs font-medium text-slate-700 transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex items-start gap-3.5 ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-1">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-3xl rounded-2xl p-4 ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-none shadow-sm'
                      : 'bg-slate-100/90 border border-slate-200 text-slate-900 rounded-bl-none'
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap leading-relaxed">
                    {msg.content}
                  </div>

                  {/* Source Citations & Expandable Passages for Assistant Messages */}
                  {msg.role === 'assistant' &&
                    msg.sources &&
                    msg.sources.length > 0 && (
                      <div className="mt-4 pt-3.5 border-t border-slate-200/90 space-y-2">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                          Verified Source Citations ({msg.sources.length})
                        </p>
                        <div className="space-y-2">
                          {msg.sources.map((src, idx) => (
                            <SourceCitationCard
                              key={`${msg.id}-src-${src.chunk_id}-${idx}`}
                              source={src}
                              index={idx}
                            />
                          ))}
                        </div>
                      </div>
                    )}

                  {/* Bonus: Helpful / Not Helpful Feedback Controls */}
                  {msg.role === 'assistant' && (
                    <div className="mt-3 pt-2.5 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
                      <span>
                        {new Date(msg.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <span>Helpful?</span>
                        <button
                          type="button"
                          onClick={() => handleFeedback(msg.id, 'helpful')}
                          className={`p-1 rounded hover:bg-slate-200 transition-colors ${
                            msg.feedback === 'helpful'
                              ? 'text-emerald-600 bg-emerald-50 font-semibold'
                              : 'text-slate-500'
                          }`}
                          title="Mark answer as helpful"
                        >
                          <ThumbsUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleFeedback(msg.id, 'not_helpful')}
                          className={`p-1 rounded hover:bg-slate-200 transition-colors ${
                            msg.feedback === 'not_helpful'
                              ? 'text-rose-600 bg-rose-50 font-semibold'
                              : 'text-slate-500'
                          }`}
                          title="Mark answer as not helpful"
                        >
                          <ThumbsDown className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-xl bg-slate-800 text-white flex items-center justify-center shrink-0 mt-1">
                    <UserIcon className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {isSending && (
            <div className="flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="rounded-2xl rounded-bl-none bg-slate-100 border border-slate-200 px-4 py-3 flex items-center gap-2.5 text-xs font-medium text-slate-600">
                <Loader2 className="w-4 h-4 text-indigo-600 animate-spin" />
                <span>
                  Searching pgvector chunks and synthesizing grounded response...
                </span>
              </div>
            </div>
          )}

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 flex items-center gap-2.5 text-xs text-rose-800">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Input Form */}
        <form
          onSubmit={handleSend}
          className="p-4 border-t border-slate-200 bg-slate-50/70 flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isSending}
            placeholder="Ask a question about uploaded policy documents..."
            className="flex-1 px-4 py-3 rounded-xl border border-slate-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!input.trim() || isSending}
            className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold inline-flex items-center gap-2 shadow-sm transition-colors"
          >
            {isSending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span>Send</span>
          </button>
        </form>
      </div>
    </div>
  );
};
