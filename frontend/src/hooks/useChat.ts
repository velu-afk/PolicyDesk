import { useCallback, useState } from 'react';
import {
  ChatMessage,
  ConversationSummary,
  RetrievalMetadata,
} from '../types';
import { chatService } from '../services/chatService';

export function useChat() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lastRetrievalMeta, setLastRetrievalMeta] = useState<RetrievalMetadata | null>(null);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConversations = useCallback(async () => {
    try {
      const list = await chatService.listConversations();
      setConversations(list);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }, []);

  const selectConversation = useCallback(async (conversationId: number) => {
    setIsLoadingHistory(true);
    setError(null);
    try {
      const detail = await chatService.getConversation(conversationId);
      setActiveConversationId(detail.id);
      setMessages(detail.messages);
      setLastRetrievalMeta(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load conversation');
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  const startNewConversation = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
    setLastRetrievalMeta(null);
    setError(null);
  }, []);

  const sendQuestion = useCallback(
    async (question: string, documentIds?: number[]) => {
      const trimmed = question.trim();
      if (!trimmed || isSending) return null;

      setIsSending(true);
      setError(null);

      // Optimistic user message bubble
      const tempUserMsg: ChatMessage = {
        id: Date.now(),
        conversation_id: activeConversationId || 0,
        role: 'user',
        content: trimmed,
        sources: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, tempUserMsg]);

      try {
        const res = await chatService.askQuestion({
          question: trimmed,
          conversation_id: activeConversationId,
          document_ids: documentIds && documentIds.length > 0 ? documentIds : null,
        });

        setActiveConversationId(res.conversation_id);
        setLastRetrievalMeta(res.retrieval_metadata);

        const assistantMsg: ChatMessage = {
          id: res.message_id,
          conversation_id: res.conversation_id,
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          created_at: res.created_at,
        };

        setMessages((prev) => [...prev, assistantMsg]);
        await fetchConversations();
        return res;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'An unexpected error occurred while generating the answer.';
        setError(message);
        // Remove optimistic message on failure so user isn't stuck
        setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
        throw err;
      } finally {
        setIsSending(false);
      }
    },
    [activeConversationId, fetchConversations, isSending]
  );

  const rateMessage = useCallback(
    async (messageId: number, feedback: 'helpful' | 'not_helpful') => {
      const updated = await chatService.submitFeedback(messageId, feedback);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, feedback: updated.feedback } : m))
      );
    },
    []
  );

  return {
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
  };
}
