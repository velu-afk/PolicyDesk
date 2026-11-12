import React, { useCallback, useEffect, useState } from 'react';
import {
  FileText,
  Trash2,
  Eye,
  X,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
} from 'lucide-react';
import { adminService } from '../services/adminService';
import { DocumentDetail, DocumentItem } from '../types';
import { FileUploader } from '../components/FileUploader';
import { useToast } from '../contexts/ToastContext';

export const DocumentManagementPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState<DocumentDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const { showToast } = useToast();

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const list = await adminService.listDocuments();
      setDocuments(list);
    } catch (err) {
      showToast(
        'error',
        'Failed to load documents',
        err instanceof Error ? err.message : undefined
      );
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleInspect = async (docId: number) => {
    setLoadingDetail(true);
    try {
      const detail = await adminService.getDocumentDetail(docId);
      setSelectedDoc(detail);
    } catch (err) {
      showToast(
        'error',
        'Could not load document chunks',
        err instanceof Error ? err.message : undefined
      );
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDelete = async (doc: DocumentItem) => {
    setDeletingId(doc.id);
    try {
      const res = await adminService.deleteDocument(doc.id);
      showToast('success', 'Document Deleted', res.message);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      if (selectedDoc?.id === doc.id) {
        setSelectedDoc(null);
      }
    } catch (err) {
      showToast(
        'error',
        'Delete Failed',
        err instanceof Error ? err.message : undefined
      );
    } finally {
      setDeletingId(null);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Document Management</h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload PDF or TXT policy documents, inspect extracted overlapping chunks, or remove obsolete documents and their pgvector embeddings.
        </p>
      </div>

      <FileUploader onUploadSuccess={() => fetchDocuments()} />

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            Ingested Repository ({documents.length})
          </h2>
        </div>

        {loading ? (
          <div className="p-12 text-center text-sm text-slate-500">
            Loading document inventory...
          </div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-slate-400 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700">
              No documents in the repository
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Upload a PDF or TXT document above to populate the knowledge base.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  <th className="py-3 px-6">Filename & Auto-Summary</th>
                  <th className="py-3 px-4">Format</th>
                  <th className="py-3 px-4 text-right">Size</th>
                  <th className="py-3 px-4 text-right">Pages</th>
                  <th className="py-3 px-4 text-right">Chunks</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Uploaded</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/80">
                    <td className="py-3.5 px-6 max-w-md">
                      <div className="font-semibold text-slate-900 flex items-center gap-2">
                        <FileText className="w-4 h-4 text-indigo-600 shrink-0" />
                        <span className="truncate">{doc.filename}</span>
                      </div>
                      {doc.summary && (
                        <p className="text-slate-500 text-[11px] mt-1 line-clamp-2">
                          {doc.summary}
                        </p>
                      )}
                      {doc.error_message && (
                        <p className="text-rose-600 text-[11px] mt-1">
                          Error: {doc.error_message}
                        </p>
                      )}
                    </td>
                    <td className="py-3.5 px-4 uppercase font-mono font-semibold text-slate-600">
                      {doc.file_type}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-slate-600">
                      {formatBytes(doc.file_size)}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-slate-600">
                      {doc.page_count ?? 1}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-semibold text-indigo-700">
                      {doc.chunk_count}
                    </td>
                    <td className="py-3.5 px-4">
                      {doc.processing_status === 'processed' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3" />
                          Processed
                        </span>
                      ) : doc.processing_status === 'failed' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                          <AlertCircle className="w-3 h-3" />
                          Failed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                          <Clock className="w-3 h-3" />
                          Processing
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                      {new Date(doc.upload_timestamp).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-6 text-right whitespace-nowrap">
                      <div className="inline-flex items-center gap-2">
                        <button
                          onClick={() => handleInspect(doc.id)}
                          disabled={loadingDetail}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-700 font-semibold transition-colors"
                          title="Inspect chunks"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Chunks</span>
                        </button>
                        <button
                          onClick={() => handleDelete(doc)}
                          disabled={deletingId === doc.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold transition-colors disabled:opacity-50"
                          title="Delete document and embeddings"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>{deletingId === doc.id ? 'Deleting...' : 'Delete'}</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Chunk Inspector Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Layers className="w-5 h-5 text-indigo-600" />
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    {selectedDoc.filename}
                  </h3>
                  <p className="text-xs text-slate-500">
                    {selectedDoc.chunks.length} indexed chunks • {selectedDoc.page_count || 1} page(s)
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedDoc(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              {selectedDoc.summary && (
                <div className="p-4 rounded-xl bg-indigo-50/70 border border-indigo-100">
                  <p className="text-xs font-bold uppercase tracking-wider text-indigo-800 mb-1">
                    Document Summary
                  </p>
                  <p className="text-xs text-indigo-950 leading-relaxed">
                    {selectedDoc.summary}
                  </p>
                </div>
              )}

              {selectedDoc.chunks.map((chunk) => (
                <div
                  key={chunk.id}
                  className="p-4 rounded-xl border border-slate-200 bg-slate-50"
                >
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-600 mb-2">
                    <span>Chunk #{chunk.chunk_index}</span>
                    <span>Page {chunk.page_number ?? 1}</span>
                  </div>
                  <pre className="text-xs text-slate-800 font-mono whitespace-pre-wrap leading-relaxed bg-white p-3 rounded-lg border border-slate-200">
                    {chunk.chunk_text}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
