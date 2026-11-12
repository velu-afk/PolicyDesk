export type UserRole = 'admin' | 'user';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export type ProcessingStatus = 'processing' | 'processed' | 'failed';

export interface DocumentItem {
  id: number;
  filename: string;
  file_type: 'pdf' | 'txt';
  file_size: number;
  page_count?: number | null;
  chunk_count: number;
  summary?: string | null;
  error_message?: string | null;
  uploaded_by?: number | null;
  uploader_name?: string | null;
  upload_timestamp: string;
  processing_status: ProcessingStatus;
}

export interface DocumentChunkPreview {
  id: number;
  document_id: number;
  chunk_index: number;
  page_number?: number | null;
  chunk_text: string;
  metadata?: Record<string, unknown> | null;
}

export interface DocumentDetail extends DocumentItem {
  chunks: DocumentChunkPreview[];
}

export interface AdminStats {
  total_documents: number;
  processed_documents: number;
  failed_documents: number;
  processing_documents: number;
  total_chunks: number;
  total_users: number;
  total_conversations: number;
  recent_uploads: DocumentItem[];
}

export interface SourceAttribution {
  chunk_id: number;
  source_document_id: number;
  source_document_name: string;
  relevant_passage: string;
  page_number?: number | null;
  chunk_index: number;
  similarity_score: number;
}

export interface RetrievalMetadata {
  query_embedding_model: string;
  llm_model: string;
  similarity_threshold: number;
  top_k_requested: number;
  chunks_evaluated: number;
  chunks_above_threshold: number;
  top_similarity_score?: number | null;
  found_in_documents: boolean;
}

export interface AskQuestionRequest {
  question: string;
  conversation_id?: number | null;
  document_ids?: number[] | null;
}

export interface AskQuestionResponse {
  answer: string;
  conversation_id: number;
  message_id: number;
  sources: SourceAttribution[];
  retrieval_metadata: RetrievalMetadata;
  created_at: string;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceAttribution[] | null;
  feedback?: 'helpful' | 'not_helpful' | null;
  created_at: string;
}

export interface ConversationSummary {
  id: number;
  user_id: number;
  title: string;
  message_count: number;
  created_at: string;
}

export interface ConversationDetail {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  messages: ChatMessage[];
}
