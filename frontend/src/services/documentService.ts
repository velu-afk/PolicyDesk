import { apiFetch } from './api';
import { DocumentDetail, DocumentItem } from '../types';

export const documentService = {
  async listProcessedDocuments(): Promise<DocumentItem[]> {
    return apiFetch<DocumentItem[]>('/api/documents');
  },

  async getDocumentDetail(documentId: number): Promise<DocumentDetail> {
    return apiFetch<DocumentDetail>(`/api/documents/${documentId}`);
  },
};
