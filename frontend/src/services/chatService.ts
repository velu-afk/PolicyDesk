import { apiFetch } from './api';
import {
  AskQuestionRequest,
  AskQuestionResponse,
  ChatMessage,
  ConversationDetail,
  ConversationSummary,
} from '../types';

export const chatService = {
  async askQuestion(payload: AskQuestionRequest): Promise<AskQuestionResponse> {
    return apiFetch<AskQuestionResponse>('/api/chat/ask', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async listConversations(): Promise<ConversationSummary[]> {
    return apiFetch<ConversationSummary[]>('/api/chat/conversations');
  },

  async getConversation(conversationId: number): Promise<ConversationDetail> {
    return apiFetch<ConversationDetail>(`/api/chat/conversations/${conversationId}`);
  },

  async deleteConversation(conversationId: number): Promise<{
    message: string;
    deleted_conversation_id: number;
  }> {
    return apiFetch(`/api/chat/conversations/${conversationId}`, {
      method: 'DELETE',
    });
  },

  async submitFeedback(
    messageId: number,
    feedback: 'helpful' | 'not_helpful'
  ): Promise<ChatMessage> {
    return apiFetch<ChatMessage>(`/api/chat/messages/${messageId}/feedback`, {
      method: 'PATCH',
      body: JSON.stringify({ feedback }),
    });
  },
};
