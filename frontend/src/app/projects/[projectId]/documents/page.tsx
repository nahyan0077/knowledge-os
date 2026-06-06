'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/shared/lib/store';
import { apiClient } from '@/shared/api/client';
import { Document, DocumentListResponse, DocumentVersion } from '@/shared/types';
import { useParams } from 'next/navigation';
import {
  FileText,
  UploadCloud,
  History,
  Trash2,
  AlertTriangle,
  FolderOpen,
  X,
  FileDown,
  Layers,
  CheckCircle,
} from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

const uploadSchema = z.object({
  name: z.string().min(1, 'Document name is required').max(255, 'Name cannot exceed 255 characters'),
});

type UploadFormValues = z.infer<typeof uploadSchema>;

export default function DocumentExplorerPage() {
  const params = useParams();
  const queryClient = useQueryClient();
  const projectId = params?.projectId as string;
  const { organization } = useAuthStore();

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [isVersionsOpen, setIsVersionsOpen] = useState(false);
  const [versionFile, setVersionFile] = useState<File | null>(null);
  const [versionFileError, setVersionFileError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors }, reset } = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
  });

  // Query: list documents
  const { data, isLoading, error } = useQuery<DocumentListResponse>({
    queryKey: ['documents', projectId, organization?.id],
    queryFn: () => apiClient<DocumentListResponse>(`/projects/${projectId}/documents`, {
      params: { organization_id: organization?.id },
    }),
    enabled: !!projectId && !!organization?.id,
  });

  // Query: list versions of selected document
  const { data: versions, isLoading: isVersionsLoading } = useQuery<DocumentVersion[]>({
    queryKey: ['document-versions', selectedDoc?.id],
    queryFn: () => apiClient<DocumentVersion[]>(`/documents/${selectedDoc?.id}/versions`),
    enabled: !!selectedDoc?.id && isVersionsOpen,
  });

  // Mutation: upload first document
  const uploadMutation = useMutation({
    mutationFn: (values: UploadFormValues) => {
      if (!uploadFile) throw new Error('File is required');
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('name', values.name);
      formData.append('organization_id', organization?.id || '');

      return apiClient<Document>(`/projects/${projectId}/documents`, {
        method: 'POST',
        body: formData,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', projectId, organization?.id] });
      setUploadFile(null);
      reset();
    },
  });

  // Mutation: upload new version
  const uploadVersionMutation = useMutation({
    mutationFn: () => {
      if (!versionFile || !selectedDoc) throw new Error('File and Document are required');
      const formData = new FormData();
      formData.append('file', versionFile);

      return apiClient<DocumentVersion>(`/projects/${projectId}/documents/${selectedDoc.id}/versions`, {
        method: 'POST',
        body: formData,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-versions', selectedDoc?.id] });
      queryClient.invalidateQueries({ queryKey: ['documents', projectId, organization?.id] });
      setVersionFile(null);
    },
  });

  // Mutation: delete document
  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => apiClient<void>(`/documents/${documentId}`, {
      method: 'DELETE',
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', projectId, organization?.id] });
      if (selectedDoc) {
        setIsVersionsOpen(false);
        setSelectedDoc(null);
      }
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setUploadFile(file);
    setFileError(null);
  };

  const handleVersionFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setVersionFile(file);
    setVersionFileError(null);
  };

  const onUploadSubmit = (values: UploadFormValues) => {
    if (!uploadFile) {
      setFileError('Please select a file to upload');
      return;
    }
    uploadMutation.mutate(values);
  };

  const onVersionUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!versionFile) {
      setVersionFileError('Please select a file to upload');
      return;
    }
    uploadVersionMutation.mutate();
  };

  const openVersionsDrawer = (doc: Document) => {
    setSelectedDoc(doc);
    setIsVersionsOpen(true);
    setVersionFile(null);
    setVersionFileError(null);
  };

  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  return (
    <div className="flex-1 flex flex-col p-6 min-h-0 relative">
      <div className="flex flex-col gap-6 lg:flex-row flex-1 min-h-0">
        
        {/* Document List Panel */}
        <div className="flex-1 flex flex-col bg-zinc-900/30 border border-zinc-900 rounded-2xl p-6 min-h-0">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-indigo-400" />
              <span>Documents</span>
            </h2>
            <p className="text-xs text-zinc-500 mt-1">Manage, delete, and view version histories of files uploaded to this workspace.</p>
          </div>

          <div className="flex-1 overflow-y-auto mt-6 min-h-0 pr-1">
            {isLoading ? (
              <div className="h-full flex items-center justify-center py-20">
                <div className="flex flex-col items-center gap-3">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent"></div>
                  <span className="text-xs text-zinc-500">Retrieving documents...</span>
                </div>
              </div>
            ) : error ? (
              <div className="h-full flex items-center justify-center py-16">
                <div className="max-w-xs text-center p-6 rounded-xl bg-zinc-900 border border-zinc-800">
                  <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-2" />
                  <p className="text-red-400 text-xs font-semibold">Failed to fetch documents</p>
                  <p className="text-zinc-500 text-[10px] mt-1">{(error as any).message || 'An error occurred.'}</p>
                </div>
              </div>
            ) : !data || data.items.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center py-20 text-center">
                <div className="h-10 w-10 rounded-xl bg-zinc-900 border border-zinc-850 flex items-center justify-center mb-3 text-zinc-600">
                  <FileText className="h-5 w-5" />
                </div>
                <h4 className="text-sm font-semibold text-zinc-300">No documents indexed</h4>
                <p className="text-zinc-500 text-xs mt-1 max-w-xs leading-relaxed">
                  Use the upload form to add document knowledge. Supported files include PDF, TXT, DOCX, and CSV.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {data.items.map((doc) => (
                  <div
                    key={doc.id}
                    className="group flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 rounded-xl bg-zinc-900/40 hover:bg-zinc-900 border border-zinc-900 hover:border-zinc-850 transition-all gap-4"
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="h-9 w-9 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center justify-center text-zinc-400 shrink-0">
                        <FileText className="h-4.5 w-4.5" />
                      </div>
                      <div className="truncate text-left pl-1">
                        <h4 className="text-sm font-semibold text-zinc-200 truncate group-hover:text-indigo-400 transition-colors">
                          {doc.name}
                        </h4>
                        <p className="text-[10px] text-zinc-500 mt-0.5">
                          Added {new Date(doc.created_at).toLocaleDateString()} at {new Date(doc.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 justify-end">
                      <button
                        onClick={() => openVersionsDrawer(doc)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-950 hover:bg-zinc-850 border border-zinc-850 hover:border-zinc-700 text-xs font-semibold text-zinc-400 hover:text-zinc-200 transition-all cursor-pointer"
                      >
                        <History className="h-3.5 w-3.5 text-zinc-500" />
                        <span>History</span>
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Are you sure you want to delete "${doc.name}"?`)) {
                            deleteMutation.mutate(doc.id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        className="flex items-center justify-center p-2 rounded-lg hover:bg-red-950/20 text-zinc-500 hover:text-red-400 border border-transparent hover:border-red-950 transition-all cursor-pointer"
                        title="Delete Document"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Upload Form Panel (Desktop Right Side, Mobile Bottom) */}
        <div className="w-full lg:w-80 bg-zinc-900/30 border border-zinc-900 rounded-2xl p-6 shrink-0 flex flex-col h-fit">
          <h3 className="text-md font-bold text-white flex items-center gap-2">
            <UploadCloud className="h-5 w-5 text-indigo-400" />
            <span>Upload Document</span>
          </h3>
          <p className="text-xs text-zinc-500 mt-1">Add a new document to start querying it with AI.</p>

          {uploadMutation.isError && (
            <div className="mt-4 p-3 rounded-lg bg-red-950/40 border border-red-950 text-red-200 text-xs">
              {(uploadMutation.error as any).message || 'Failed to upload document'}
            </div>
          )}

          {uploadMutation.isSuccess && (
            <div className="mt-4 p-3 rounded-lg bg-emerald-950/40 border border-emerald-950 text-emerald-200 text-xs flex items-center gap-1.5">
              <CheckCircle className="h-4 w-4 text-emerald-400" />
              <span>Document uploaded successfully!</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onUploadSubmit)} className="space-y-4 mt-6">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-zinc-400 mb-2">
                Document Name
              </label>
              <input
                type="text"
                {...register('name')}
                className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-xs"
                placeholder="e.g., Q2 Financial Report"
                disabled={uploadMutation.isPending}
              />
              {errors.name && (
                <p className="mt-1 text-[10px] text-red-400">{errors.name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-zinc-400 mb-2">
                File Input
              </label>
              <div className="relative border border-zinc-800 rounded-xl p-4 bg-zinc-950/80 hover:bg-zinc-950/50 hover:border-zinc-700 transition-colors flex flex-col items-center justify-center text-center cursor-pointer min-h-[140px]">
                <input
                  type="file"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  disabled={uploadMutation.isPending}
                />
                <UploadCloud className="h-8 w-8 text-zinc-600 mb-2" />
                <span className="text-xs font-semibold text-zinc-300">
                  {uploadFile ? uploadFile.name : 'Select or drop a file'}
                </span>
                <span className="text-[10px] text-zinc-500 mt-1">
                  {uploadFile ? formatBytes(uploadFile.size) : 'PDF, TXT, DOCX up to 50MB'}
                </span>
              </div>
              {fileError && (
                <p className="mt-1 text-[10px] text-red-400">{fileError}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={uploadMutation.isPending}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-lg shadow-indigo-500/10 hover:shadow-indigo-500/20 transition-all cursor-pointer disabled:opacity-50"
            >
              {uploadMutation.isPending ? 'Uploading...' : 'Upload File'}
            </button>
          </form>
        </div>
      </div>

      {/* Slide-out Versions Drawer */}
      {isVersionsOpen && selectedDoc && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-zinc-900 border-l border-zinc-800 h-full flex flex-col p-6 shadow-2xl relative animate-in slide-in-from-right duration-300">
            <button
              onClick={() => {
                setIsVersionsOpen(false);
                setSelectedDoc(null);
              }}
              className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-200 rounded-lg p-1 transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="mb-6 pr-6">
              <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest flex items-center gap-1.5 mb-1.5">
                <Layers className="h-3.5 w-3.5" />
                <span>Version History</span>
              </span>
              <h3 className="text-lg font-bold text-white line-clamp-1">{selectedDoc.name}</h3>
              <p className="text-zinc-500 text-[10px] mt-0.5">Manage versions and inspect deployment state.</p>
            </div>

            {/* Version Upload Form */}
            <div className="p-4 border border-zinc-800 rounded-xl bg-zinc-950/20 mb-6 shrink-0">
              <h4 className="text-xs font-bold text-zinc-300 mb-2">Upload New Version</h4>
              <form onSubmit={onVersionUploadSubmit} className="flex flex-col sm:flex-row gap-3">
                <div className="relative border border-zinc-800 rounded-lg p-2 bg-zinc-950 hover:bg-zinc-900 hover:border-zinc-700 transition-colors flex items-center justify-center text-center cursor-pointer flex-1 min-h-[38px]">
                  <input
                    type="file"
                    onChange={handleVersionFileChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    disabled={uploadVersionMutation.isPending}
                  />
                  <span className="text-[11px] font-medium text-zinc-350 truncate max-w-[200px]">
                    {versionFile ? versionFile.name : 'Select updated file'}
                  </span>
                </div>
                <button
                  type="submit"
                  disabled={uploadVersionMutation.isPending || !versionFile}
                  className="py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all cursor-pointer disabled:opacity-50 shrink-0"
                >
                  {uploadVersionMutation.isPending ? 'Uploading...' : 'Upload'}
                </button>
              </form>
              {versionFileError && (
                <p className="mt-1 text-[10px] text-red-400">{versionFileError}</p>
              )}
            </div>

            {/* Versions List */}
            <div className="flex-1 overflow-y-auto pr-1 space-y-4">
              {isVersionsLoading ? (
                <div className="h-32 flex items-center justify-center">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent"></div>
                </div>
              ) : !versions || versions.length === 0 ? (
                <p className="text-zinc-500 text-xs text-center py-12">No version history found.</p>
              ) : (
                <div className="space-y-3">
                  {versions.map((ver) => (
                    <div
                      key={ver.id}
                      className="p-4 rounded-xl bg-zinc-950/50 border border-zinc-850 flex flex-col gap-2 relative overflow-hidden group hover:border-zinc-800 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-extrabold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/15">
                          v{ver.version_number}
                        </span>
                        <span className={`text-[10px] font-bold uppercase tracking-wider ${
                          ver.status === 'uploaded' || ver.status === 'indexed'
                            ? 'text-emerald-400'
                            : ver.status === 'processing'
                            ? 'text-yellow-400'
                            : ver.status === 'failed'
                            ? 'text-red-400'
                            : 'text-zinc-500'
                        }`}>
                          {ver.status}
                        </span>
                      </div>

                      <div className="text-zinc-350 text-xs mt-1 space-y-1">
                        <div className="flex justify-between items-center text-[10px] text-zinc-500">
                          <span>File:</span>
                          <span className="text-zinc-350 truncate max-w-[250px] font-medium" title={ver.source_filename}>
                            {ver.source_filename}
                          </span>
                        </div>
                        <div className="flex justify-between items-center text-[10px] text-zinc-500">
                          <span>Size:</span>
                          <span className="text-zinc-350 font-medium">{formatBytes(ver.size_bytes)}</span>
                        </div>
                        <div className="flex justify-between items-center text-[10px] text-zinc-500">
                          <span>Uploaded:</span>
                          <span className="text-zinc-350 font-medium">
                            {new Date(ver.created_at).toLocaleDateString()} {new Date(ver.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
