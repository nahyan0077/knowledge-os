'use client';

import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/shared/lib/store';
import { apiClient } from '@/shared/api/client';
import { Conversation } from '@/shared/types';
import { useParams, useRouter } from 'next/navigation';
import { MessageSquare, Plus, Sparkles } from 'lucide-react';

export default function ConversationsLandingPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.projectId as string;
  const { organization } = useAuthStore();
  const queryClient = useQueryClient();

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
  });

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-zinc-950/20">
      {/* Glow effect */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full bg-indigo-500/5 blur-[80px] pointer-events-none"></div>

      <div className="max-w-md space-y-6 relative z-10">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-zinc-900 border border-zinc-800 text-indigo-400 shadow-xl shadow-indigo-500/5 animate-pulse">
          <MessageSquare className="h-6 w-6" />
        </div>
        
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white sm:text-2xl flex items-center justify-center gap-2">
            <span>AI Knowledge Assistant</span>
            <Sparkles className="h-4.5 w-4.5 text-indigo-400" />
          </h2>
          <p className="text-zinc-500 text-xs mt-2 leading-relaxed">
            Start a conversational chat session grounded in your project's uploaded documents. Query definitions, compare version differences, or summarize documents.
          </p>
        </div>

        <button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
          className="mx-auto flex items-center gap-2 py-2.5 px-5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/15 hover:shadow-indigo-500/25 transition-all cursor-pointer disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          <span>{createMutation.isPending ? 'Creating Chat...' : 'Start New Conversation'}</span>
        </button>
      </div>
    </div>
  );
}
