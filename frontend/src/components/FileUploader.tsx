import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import { adminService } from '../services/adminService';
import { DocumentItem } from '../types';
import { useToast } from '../contexts/ToastContext';

interface FileUploaderProps {
  onUploadSuccess: (doc: DocumentItem) => void;
}

export const FileUploader: React.FC<FileUploaderProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStage, setUploadStage] = useState<string>('');
  const [lastUploaded, setLastUploaded] = useState<DocumentItem | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { showToast } = useToast();

  const validateAndUpload = async (file: File) => {
    setUploadError(null);
    setLastUploaded(null);

    const ext = file.name.toLowerCase().split('.').pop();
    if (ext !== 'pdf' && ext !== 'txt') {
      const msg = `Unsupported file format (.${ext}). Please upload a PDF (.pdf) or Plain Text (.txt) document.`;
      setUploadError(msg);
      showToast('error', 'Invalid File Format', msg);
      return;
    }

    if (file.size === 0) {
      const msg = 'The selected file is empty (0 bytes).';
      setUploadError(msg);
      showToast('error', 'Empty Document', msg);
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      const msg = 'File size exceeds the 20 MB maximum upload limit.';
      setUploadError(msg);
      showToast('error', 'File Too Large', msg);
      return;
    }

    setIsUploading(true);
    setUploadStage('Extracting text, chunking with overlap & generating Gemini embeddings...');

    try {
      const uploadedDoc = await adminService.uploadDocument(file);
      setLastUploaded(uploadedDoc);
      showToast(
        'success',
        'Document Ingested Successfully',
        `${uploadedDoc.filename} (${uploadedDoc.chunk_count} semantic chunks stored)`
      );
      onUploadSuccess(uploadedDoc);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to process document.';
      setUploadError(msg);
      showToast('error', 'Ingestion Failed', msg);
    } finally {
      setIsUploading(false);
      setUploadStage('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (isUploading) return;
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      await validateAndUpload(files[0]);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-slate-900">
            Ingest Policy Document
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload PDF or TXT policies. Text is automatically extracted, chunked with overlap, and embedded into pgvector.
          </p>
        </div>
        <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-100">
          PDF / TXT • Max 20 MB
        </span>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!isUploading) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
          isDragging
            ? 'border-indigo-600 bg-indigo-50/70'
            : isUploading
            ? 'border-indigo-300 bg-slate-50 cursor-wait'
            : 'border-slate-300 hover:border-indigo-500 hover:bg-slate-50/80'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,application/pdf,text/plain"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) validateAndUpload(file);
          }}
        />

        {isUploading ? (
          <div className="flex flex-col items-center gap-3 py-2">
            <Loader2 className="w-9 h-9 text-indigo-600 animate-spin" />
            <div>
              <p className="text-sm font-semibold text-slate-900">
                Processing Document Pipeline...
              </p>
              <p className="text-xs text-slate-500 mt-1">{uploadStage}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2.5">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">
                Drag and drop a policy document here, or{' '}
                <span className="text-indigo-600 underline">browse files</span>
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Supports native PDF documents (via PyMuPDF) and UTF-8 plain text files (.txt)
              </p>
            </div>
          </div>
        )}
      </div>

      {lastUploaded && (
        <div className="mt-4 p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="text-xs text-emerald-900">
            <p className="font-semibold">
              Ingested: {lastUploaded.filename} ({lastUploaded.chunk_count} chunks,{' '}
              {lastUploaded.page_count || 1} page{lastUploaded.page_count === 1 ? '' : 's'})
            </p>
            {lastUploaded.summary && (
              <p className="mt-1 text-emerald-800 leading-relaxed">
                <span className="font-semibold">Auto-Summary:</span> {lastUploaded.summary}
              </p>
            )}
          </div>
        </div>
      )}

      {uploadError && (
        <div className="mt-4 p-3.5 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="text-xs text-rose-900">
            <p className="font-semibold">Upload Rejected</p>
            <p className="mt-0.5">{uploadError}</p>
          </div>
        </div>
      )}
    </div>
  );
};
