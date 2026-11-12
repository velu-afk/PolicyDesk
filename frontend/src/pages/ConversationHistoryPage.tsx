import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  History,
  MessageSquare,
  Trash2,
  ArrowRight,
  Calendar,
} from 'lucide-react';
import { chatService } from '../services/chatService';
import { ConversationSummary } from '../types';
import { useToast } from '../contexts/ToastContext';

export const ConversationHistoryPage: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const { showToast } = useToast();

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await chatService.listConversations();
      setConversations(data);
    } catch (err) {
      showToast(
        'error',
        'Failed to load conversation history',
        err instanceof Error ? err.message : undefined
      );
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await chatService.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      showToast('success', 'Conversation Deleted');
    } catch (err) {
      showToast(
        'error',
        'Failed to delete conversation',
        err instanceof Error ? err.message : undefined
      );
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Conversation History</h1>
          <p className="text-sm text-slate-500 mt-1">
            Review or resume your previous policy Q&A threads and their source attributions.
          </p>
        </div>
        <Link
          to="/chat"
          className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold inline-flex items-center gap-2 shadow-sm transition-colors"
        >
          <span>Start New Chat</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-slate-500">
            Loading saved conversations...
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-12 text-center">
            <History className="w-10 h-10 text-slate-400 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700">
              No saved conversations yet
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Questions you ask in the AI Policy Assistant are automatically saved here.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className="p-5 flex items-center justify-between gap-4 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-start gap-3.5 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center shrink-0 mt-0.5">
                    <MessageSquare className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <Link
                      to={`/chat?conversationId=${conv.id}`}
                      className="text-sm font-bold text-slate-900 hover:text-indigo-600 truncate block"
                    >
                      {conv.title}
                    </Link>
                    <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {new Date(conv.created_at).toLocaleString()}
                      </span>
                      <span>•</span>
                      <span>{conv.message_count} messages</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    to={`/chat?conversationId=${conv.id}`}
                    className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-xs font-semibold text-slate-700 transition-colors"
                  >
                    Open Thread
                  </Link>
                  <button
                    onClick={() => handleDelete(conv.id)}
                    disabled={deletingId === conv.id}
                    className="p-1.5 rounded-lg border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-600 transition-colors disabled:opacity-50"
                    title="Delete thread"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
