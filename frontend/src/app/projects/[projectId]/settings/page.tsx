'use client';

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore, useUiStore } from '@/shared/lib/store';
import { apiClient } from '@/shared/api/client';
import { Project } from '@/shared/types';
import { useParams, useRouter } from 'next/navigation';
import { Settings, Trash2, ShieldAlert, CheckCircle, AlertTriangle } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

const settingsSchema = z.object({
  name: z.string().min(1, 'Project name is required').max(160, 'Name cannot exceed 160 characters'),
  description: z.string().max(4000, 'Description cannot exceed 4000 characters').optional(),
});

type SettingsFormValues = z.infer<typeof settingsSchema>;

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const projectId = params?.projectId as string;
  const { activeProject, setActiveProject } = useUiStore();

  const [updateError, setUpdateError] = useState<string | null>(null);
  const [updateSuccess, setUpdateSuccess] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors }, reset } = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
  });

  // Query: get project
  const { data: project, isLoading, error } = useQuery<Project>({
    queryKey: ['project-settings', projectId],
    queryFn: () => apiClient<Project>(`/projects/${projectId}`),
    enabled: !!projectId,
  });

  useEffect(() => {
    if (project) {
      reset({
        name: project.name,
        description: project.description || '',
      });
    }
  }, [project, reset]);

  // Mutation: update project
  const updateMutation = useMutation({
    mutationFn: (values: SettingsFormValues) => {
      const currentVersion = project?.version || 1;
      return apiClient<Project>(`/projects/${projectId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          version: currentVersion,
          name: values.name,
          description: values.description || null,
        }),
      });
    },
    onSuccess: (updatedProj) => {
      queryClient.invalidateQueries({ queryKey: ['project-settings', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      setActiveProject(updatedProj);
      setUpdateSuccess(true);
      setTimeout(() => setUpdateSuccess(false), 3000);
    },
    onError: (err: any) => {
      setUpdateError(err.message || 'Failed to update project settings.');
    },
  });

  // Mutation: delete project
  const deleteMutation = useMutation({
    mutationFn: () => apiClient<void>(`/projects/${projectId}`, {
      method: 'DELETE',
    }),
    onSuccess: () => {
      setActiveProject(null);
      router.push('/dashboard');
    },
    onError: (err: any) => {
      setDeleteError(err.message || 'Failed to delete project.');
    },
  });

  const onSubmit = (data: SettingsFormValues) => {
    setUpdateError(null);
    updateMutation.mutate(data);
  };

  const handleDeleteProject = () => {
    if (
      confirm(
        `Are you absolutely sure you want to delete "${project?.name}"? All files, index contexts, and chat history will be permanently soft-deleted.`
      )
    ) {
      setDeleteError(null);
      deleteMutation.mutate();
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent"></div>
          <span className="text-xs text-zinc-500">Loading settings...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-xs text-center p-6 rounded-xl bg-zinc-900 border border-zinc-850">
          <AlertTriangle className="h-7 w-7 text-red-400 mx-auto mb-2" />
          <p className="text-red-400 text-xs font-semibold">Failed to load project details</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 max-w-2xl w-full mx-auto space-y-8">
      {/* General Settings Card */}
      <div className="bg-zinc-900/30 border border-zinc-900 rounded-2xl p-6">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Settings className="h-5 w-5 text-indigo-400" />
          <span>Project Settings</span>
        </h2>
        <p className="text-xs text-zinc-500 mt-1">Configure project metadata and adjust workspace parameters.</p>

        {updateError && (
          <div className="mt-4 p-3 rounded-lg bg-red-950/40 border border-red-950 text-red-200 text-xs">
            {updateError}
          </div>
        )}

        {updateSuccess && (
          <div className="mt-4 p-3 rounded-lg bg-emerald-950/40 border border-emerald-950 text-emerald-200 text-xs flex items-center gap-1.5">
            <CheckCircle className="h-4 w-4 text-emerald-400" />
            <span>Settings updated successfully!</span>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-6">
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-zinc-400 mb-2">
              Project Name
            </label>
            <input
              type="text"
              {...register('name')}
              className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-xs"
              disabled={updateMutation.isPending}
            />
            {errors.name && (
              <p className="mt-1 text-[10px] text-red-400">{errors.name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-zinc-400 mb-2">
              Description
            </label>
            <textarea
              {...register('description')}
              rows={4}
              className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-xs resize-none"
              placeholder="Workspace description"
              disabled={updateMutation.isPending}
            />
            {errors.description && (
              <p className="mt-1 text-[10px] text-red-400">{errors.description.message}</p>
            )}
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="py-2 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow-lg shadow-indigo-500/10 cursor-pointer active:scale-95"
            >
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>

      {/* Danger Zone Card */}
      <div className="bg-zinc-900/10 border border-red-950/30 rounded-2xl p-6">
        <h3 className="text-md font-bold text-red-450 flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-red-450" />
          <span>Danger Zone</span>
        </h3>
        <p className="text-xs text-zinc-500 mt-1">Actions that have permanent consequences on your workspace.</p>

        {deleteError && (
          <div className="mt-4 p-3 rounded-lg bg-red-950/40 border border-red-950 text-red-200 text-xs">
            {deleteError}
          </div>
        )}

        <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 border border-red-950/40 rounded-xl bg-red-950/5">
          <div>
            <h4 className="text-xs font-bold text-zinc-200">Delete Project Workspace</h4>
            <p className="text-[10px] text-zinc-500 mt-0.5">
              Soft-deletes the project configuration. Access will be revoked immediately.
            </p>
          </div>
          <button
            onClick={handleDeleteProject}
            disabled={deleteMutation.isPending}
            className="flex items-center gap-1.5 py-2 px-4 rounded-xl bg-red-950/40 hover:bg-red-900/40 text-red-300 hover:text-red-200 text-xs font-semibold border border-red-900/30 transition-all cursor-pointer shrink-0"
          >
            <Trash2 className="h-4 w-4" />
            <span>Delete Project</span>
          </button>
        </div>
      </div>
    </div>
  );
}
