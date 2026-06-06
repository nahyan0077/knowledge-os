'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/shared/lib/store';
import { apiClient } from '@/shared/api/client';
import { Conversation, ConversationListResponse } from '@/shared/types';
import { useParams, useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  MessageSquare,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  AlertTriangle,
  FolderMinus,
} from 'lucide-react';

interface ConversationLayoutProps {
  children: React.ReactNode;
}

export default function ConversationLayout({ children }: ConversationLayoutProps) {
  const params = useParams();
  const router = useRouter();
  const pathname = usePathname();
  const projectId = params?.projectId as string;
  const activeConversationId = params?.conversationId as string;
  const { organization } = useAuthStore();
  const queryClient = useQueryClient();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);

  // Query: list conversations
  const { data, isLoading, error } = useQuery<ConversationListResponse>({
    queryKey: ['conversations', projectId, organization?.id],
    queryFn: () => apiClient<ConversationListResponse>(`/projects/${projectId}/conversations`, {
      params: { organization_id: organization?.id },
    }),
    enabled: !!projectId && !!organization?.id,
  });

  // Mutation: create conversation
  const createMutation = useMutation({
    mutationFn: () => apiClient<Conversation>(`/projects/${projectId}/conversations`, {
      method: 'POST',
      body: JSON.stringify({
        organization_id: organization?.id,
        title: 'New Conversation',
      }),
    }),
    onSuccess: (newConv) => {
      queryClient.invalidateQueries({ queryKey: ['conversations', projectId, organization?.id] });
      router.push(`/projects/${projectId}/conversations/${newConv.id}`);
    },
    onError: (err: any) => {
      setCreateError(err.message || 'Failed to create conversation');
      setTimeout(() => setCreateError(null), 3000);
    },
  });

  // Mutation: rename conversation
  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      apiClient<Conversation>(`/conversations/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ title }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations', projectId, organization?.id] });
      setEditingId(null);
    },
  });

  // Mutation: delete conversation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient<void>(`/conversations/${id}`, {
      method: 'DELETE',
    }),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['conversations', projectId, organization?.id] });
      if (activeConversationId === deletedId) {
        router.push(`/projects/${projectId}/conversations`);
      }
    },
  });

  const handleStartRename = (conv: Conversation, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleSaveRename = (id: string, e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const title = editTitle.trim();
    if (title) {
      renameMutation.mutate({ id, title });
    } else {
      setEditingId(null);
    }
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setEditingId(null);
  };

  const handleDelete = (id: string, title: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (confirm(`Delete conversation "${title}"?`)) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="flex-1 flex min-h-0 bg-zinc-950">
      {/* Left Sidebar Pane: Conversation List */}
      <div className="w-80 border-r border-zinc-900 bg-zinc-950/40 flex flex-col shrink-0 min-h-0">
        <div className="p-4 border-b border-zinc-900 flex items-center justify-between min-h-[65px] shrink-0">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Chats</h3>
            <p className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">Conversation History</p>
          </div>
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            className="flex items-center justify-center p-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-indigo-400 hover:text-indigo-350 border border-zinc-800 transition-colors cursor-pointer"
            title="Create Conversation"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>

        {createError && (
          <div className="p-3 bg-red-950/40 border-b border-red-950 text-red-400 text-xs shrink-0">
            {createError}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-2 space-y-1 pr-1.5 min-h-0">
          {isLoading ? (
            <div className="h-32 flex items-center justify-center">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent"></div>
            </div>
          ) : error ? (
            <div className="p-4 text-center">
              <AlertTriangle className="h-6 w-6 text-red-400 mx-auto mb-2" />
              <p className="text-red-400 text-xs font-medium">Failed to load chats</p>
            </div>
          ) : !data || data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-center py-16 px-4">
              <MessageSquare className="h-6 w-6 text-zinc-700 mb-2" />
              <p className="text-zinc-500 text-xs font-medium">No active conversations</p>
              <button
                onClick={() => createMutation.mutate()}
                className="mt-3 text-[10px] font-bold text-indigo-400 hover:text-indigo-300 uppercase tracking-wider cursor-pointer"
              >
                + Start New Chat
              </button>
            </div>
          ) : (
            data.items.map((conv) => {
              const isActive = activeConversationId === conv.id;
              const isEditing = editingId === conv.id;

              return (
                <div key={conv.id} className="relative group">
                  {isEditing ? (
                    <form
                      onSubmit={(e) => handleSaveRename(conv.id, e)}
                      className="flex items-center gap-1.5 p-2 rounded-xl bg-zinc-900 border border-zinc-800"
                    >
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="bg-zinc-950 text-zinc-100 text-xs px-2 py-1 rounded-lg border border-zinc-800 focus:outline-none focus:border-indigo-500 flex-1 min-w-0"
                        autoFocus
                      />
                      <button
                        type="submit"
                        disabled={renameMutation.isPending}
                        className="text-emerald-400 hover:text-emerald-350 p-0.5 rounded cursor-pointer"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={handleCancelRename}
                        className="text-red-400 hover:text-red-350 p-0.5 rounded cursor-pointer"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </form>
                  ) : (
                    <Link
                      href={`/projects/${projectId}/conversations/${conv.id}`}
                      className={`flex items-center justify-between p-3 rounded-xl text-xs font-semibold border transition-all ${
                        isActive
                          ? 'bg-zinc-900 border-zinc-800 text-white shadow-sm'
                          : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <MessageSquare className={`h-4 w-4 shrink-0 ${isActive ? 'text-indigo-400' : 'text-zinc-500'}`} />
                        <span className="truncate max-w-[130px] pr-2">{conv.title}</span>
                      </div>
                      
                      {/* Hover Action Buttons */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => handleStartRename(conv, e)}
                          className="text-zinc-500 hover:text-zinc-200 p-0.5 rounded transition-colors cursor-pointer"
                          title="Rename Chat"
                        >
                          <Edit2 className="h-3 w-3" />
                        </button>
                        <button
                          onClick={(e) => handleDelete(conv.id, conv.title, e)}
                          className="text-zinc-500 hover:text-red-400 p-0.5 rounded transition-colors cursor-pointer"
                          title="Delete Chat"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </Link>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Pane: Conversation Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-zinc-950 relative">
        {children}
      </div>
    </div>
  );
}
