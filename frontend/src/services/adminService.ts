import { apiFetch } from './api';
import {
  AdminStats,
  DocumentDetail,
  DocumentItem,
  User,
  UserRole,
} from '../types';

export const adminService = {
  async getStats(): Promise<AdminStats> {
    return apiFetch<AdminStats>('/api/admin/stats');
  },

  async listDocuments(): Promise<DocumentItem[]> {
    return apiFetch<DocumentItem[]>('/api/admin/documents');
  },

  async getDocumentDetail(documentId: number): Promise<DocumentDetail> {
    return apiFetch<DocumentDetail>(`/api/admin/documents/${documentId}`);
  },

  async uploadDocument(file: File): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append('file', file);
    return apiFetch<DocumentItem>('/api/admin/documents/upload', {
      method: 'POST',
      body: formData,
    });
  },

  async deleteDocument(documentId: number): Promise<{
    message: string;
    deleted_document_id: number;
    deleted_chunks_count: number;
  }> {
    return apiFetch(`/api/admin/documents/${documentId}`, {
      method: 'DELETE',
    });
  },

  async listUsers(): Promise<User[]> {
    return apiFetch<User[]>('/api/admin/users');
  },

  async updateUser(
    userId: number,
    payload: { role?: UserRole; is_active?: boolean; name?: string }
  ): Promise<User> {
    return apiFetch<User>(`/api/admin/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },
};
