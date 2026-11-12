import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  CheckCircle2,
  AlertOctagon,
  Users,
  Layers,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { adminService } from '../services/adminService';
import { AdminStats } from '../types';
import { StatCard } from '../components/StatCard';
import { FileUploader } from '../components/FileUploader';

export const AdminDashboardPage: React.FC = () => {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminService.getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load admin stats:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Administrator Control Center
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Monitor document ingestion health, semantic vector index coverage, and registered users.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadStats}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 shadow-sm transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Metrics</span>
          </button>
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-xs font-semibold text-white shadow-sm transition-colors"
          >
            <span>Test RAG Assistant</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          label="Total Documents"
          value={stats?.total_documents ?? 0}
          subtitle="Uploaded PDF & TXT files"
          icon={<FileText className="w-5 h-5" />}
          accent="indigo"
        />
        <StatCard
          label="Processed Docs"
          value={stats?.processed_documents ?? 0}
          subtitle="Indexed & ready for RAG"
          icon={<CheckCircle2 className="w-5 h-5" />}
          accent="emerald"
        />
        <StatCard
          label="Failed Docs"
          value={stats?.failed_documents ?? 0}
          subtitle="Validation or parse errors"
          icon={<AlertOctagon className="w-5 h-5" />}
          accent="rose"
        />
        <StatCard
          label="Indexed Chunks"
          value={stats?.total_chunks ?? 0}
          subtitle="768-dim Gemini embeddings"
          icon={<Layers className="w-5 h-5" />}
          accent="amber"
        />
        <StatCard
          label="Registered Users"
          value={stats?.total_users ?? 0}
          subtitle={`${stats?.total_conversations ?? 0} active chat threads`}
          icon={<Users className="w-5 h-5" />}
          accent="slate"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Drag-and-Drop Document Uploader */}
        <div className="lg:col-span-5">
          <FileUploader onUploadSuccess={() => loadStats()} />
        </div>

        {/* Right: Recent Uploads Table */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Recent Document Uploads
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Latest files processed through the PyMuPDF + Gemini embedding pipeline.
              </p>
            </div>
            <Link
              to="/admin/documents"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 inline-flex items-center gap-1"
            >
              <span>Manage All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {!stats || stats.recent_uploads.length === 0 ? (
            <div className="py-12 text-center border border-dashed border-slate-200 rounded-xl">
              <FileText className="w-8 h-8 text-slate-400 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-700">
                No documents uploaded yet
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Use the upload panel on the left to ingest your first PDF or TXT policy.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    <th className="py-2.5 pr-4">Document</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3 text-right">Chunks</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 pl-3 text-right">Uploaded</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  {stats.recent_uploads.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50/80">
                      <td className="py-3 pr-4 font-semibold text-slate-900 max-w-[220px] truncate">
                        {doc.filename}
                      </td>
                      <td className="py-3 px-3 uppercase font-mono text-[11px] text-slate-600">
                        {doc.file_type}
                      </td>
                      <td className="py-3 px-3 text-right font-mono text-slate-700">
                        {doc.chunk_count}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                            doc.processing_status === 'processed'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : doc.processing_status === 'failed'
                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}
                        >
                          {doc.processing_status}
                        </span>
                      </td>
                      <td className="py-3 pl-3 text-right text-slate-500 whitespace-nowrap">
                        {new Date(doc.upload_timestamp).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
